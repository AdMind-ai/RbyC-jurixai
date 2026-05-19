import logging
from time import perf_counter
from typing import Dict

from django.conf import settings
from django.db import transaction
from openai import OpenAI
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models.assistant_thread_model import AssistantThread
from core.models.openai_chat_models import ChatConversation, ChatMessage
from core.models.usage import UsageTool
from core.services.usage_tracking import UsageTrackingService
from core.utils.s3_utils import get_presigned_urls_for_document_keys
from integrations.models import IntegrationClient
from integrations.services.ricerca_documentale_runtime import (
    build_ricerca_documentale_mcp_tool,
    build_ricerca_documentale_request_context,
    extract_ricerca_documentale_response_payload,
)


client = OpenAI(api_key=settings.OPENAI_KEY)
logger = logging.getLogger(__name__)


class AssistantMessageSerializer(serializers.Serializer):
    thread_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    content = serializers.CharField(required=True, allow_blank=False)


class AssistantStreamingView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AssistantMessageSerializer

    def post(self, request, *args, **kwargs):
        request_started_at = perf_counter()
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        prompt = serializer.validated_data["content"]
        thread_id = serializer.validated_data["thread_id"]
        integration_client = IntegrationClient.objects.filter(
            customer_code="default",
            active=True,
        ).first()
        request_context = build_ricerca_documentale_request_context(
            prompt=prompt,
            integration_client=integration_client,
        )

        logger.info(
            "[assistant_streaming] intent_detected intent_type=%s confidence=%s matched_signals=%s primary_tool=%s prefer_preview_only=%s max_documents_to_open=%s group_by=%s",
            request_context.intent_classification.intent_type,
            request_context.intent_classification.confidence,
            ",".join(request_context.intent_classification.matched_signals) or "<none>",
            request_context.retrieval_strategy.primary_tool,
            request_context.retrieval_strategy.prefer_preview_only,
            request_context.retrieval_strategy.max_documents_to_open,
            request_context.retrieval_strategy.group_by or "<none>",
        )
        logger.info(
            "[assistant_streaming] model_input_prepared original_prompt_length=%s model_input_length=%s presearch_candidates=%s related_approval_candidates=%s",
            len(prompt or ""),
            len(request_context.model_input or ""),
            len(request_context.presearch_candidates),
            len(request_context.related_approval_candidates),
        )

        with transaction.atomic():
            if thread_id:
                assistant_thread = AssistantThread.objects.filter(thread_id=thread_id).first()
                if not assistant_thread:
                    conversation_openai = client.conversations.create()
                    assistant_thread = AssistantThread.objects.create(
                        thread_id=conversation_openai.id,
                        active=True,
                    )
            else:
                conversation_openai = client.conversations.create()
                assistant_thread = AssistantThread.objects.create(
                    thread_id=conversation_openai.id,
                    active=True,
                )

            if assistant_thread.conversation:
                conversation = assistant_thread.conversation
            else:
                user = request.user
                ChatConversation.objects.filter(user=user, is_new=True).delete()
                conversation = ChatConversation.objects.create(
                    user=user,
                    name="New Chat",
                    is_new=True,
                )
                assistant_thread.conversation = conversation
                assistant_thread.save(update_fields=["conversation"])

        ChatMessage.objects.create(
            conversation=conversation,
            content=prompt,
            is_user=True,
        )

        try:
            response = client.responses.create(
                prompt={"id": settings.OPENAI_PROMPT_ID_RICERCA_DOCUMENTALE},
                input=request_context.model_input,
                conversation=assistant_thread.thread_id,
                tools=[
                    build_ricerca_documentale_mcp_tool(
                        mcp_token=request_context.mcp_token
                    )
                ],
                store=True,
                timeout=900,
            )
        except Exception as exc:
            logger.exception("Erro ao chamar OpenAI Responses API: %s", exc)
            return Response(
                {"error": "Erro ao chamar o servico de respostas externo."},
                status=502,
            )

        try:
            response_payload = extract_ricerca_documentale_response_payload(response)
        except Exception:
            logger.exception(
                "[assistant_streaming] response_parse_failed thread_id=%s",
                assistant_thread.thread_id or "<empty>",
            )
            response_payload = None

        response_text = response_payload.response_text if response_payload else ""
        response_keys = response_payload.response_keys if response_payload else []

        documents_urls = {}
        if response_keys:
            try:
                documents_urls = get_presigned_urls_for_document_keys(
                    response_keys,
                    customer_code=(request_context.customer_code or None),
                    fallback_bucket=request_context.bucket_name,
                )
            except Exception as exc:
                logger.exception("Erro ao recuperar URLs S3: %s", exc)

        citations_list = _build_citations_list(documents_urls)

        ChatMessage.objects.create(
            conversation=conversation,
            content=response_text,
            is_user=False,
            citations=citations_list,
        )

        UsageTrackingService.record_usage_event(
            user=request.user,
            tool=UsageTool.RICERCA_DOCUMENTALE,
            quantity=1,
            company=getattr(request.user, "company", None),
            metadata={
                "conversation_id": conversation.id,
            },
        )

        total_duration_ms = round((perf_counter() - request_started_at) * 1000, 2)
        logger.info(
            "[assistant_streaming] request_completed intent_type=%s total_duration_ms=%s response_text_length=%s response_keys_count=%s documents_urls_count=%s model_input_length=%s",
            request_context.intent_classification.intent_type,
            total_duration_ms,
            len(response_text or ""),
            len(response_keys),
            len(documents_urls),
            len(request_context.model_input or ""),
        )

        return Response(
            {
                "response_text": response_text,
                "documents_urls": documents_urls,
            }
        )


def _build_citations_list(documents_urls: Dict[str, str]) -> list[dict]:
    citations_list = []
    try:
        import re

        for idx, (key, url) in enumerate((documents_urls or {}).items()):
            parts = str(key).split("/") if key else [str(key)]
            filename = parts[-1] if parts else str(key)
            match = re.search(r"\.([0-9a-zA-Z]+)(?:\?|$)", filename)
            extension = match.group(1).lower() if match else ""
            citations_list.append(
                {
                    "id": f"{idx}-{filename}",
                    "title": filename,
                    "url": url,
                    "type": extension,
                }
            )
    except Exception:
        logger.exception("Erro ao normalizar documents_urls para citations_list")
    return citations_list
