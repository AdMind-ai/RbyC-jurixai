import logging
from time import perf_counter
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models.assistant_thread_model import AssistantThread
from core.utils.openai_client import client
from core.utils.s3_utils import get_presigned_urls_for_document_keys
from integrations.authentication import APIKeyAuthentication
from integrations.permissions import HasValidAPIKey
from integrations.services.ricerca_documentale_runtime import (
    build_ricerca_documentale_mcp_tool,
    build_ricerca_documentale_request_context,
    extract_ricerca_documentale_response_payload,
)
from integrations.services.usage_audit import (
    record_integration_ricerca_documentale_usage,
)


logger = logging.getLogger(__name__)


@extend_schema(
    summary="Responsavel por fornecer um endpoint para a pesquisa documental",
)
class RicercaDocumentaleView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [HasValidAPIKey]

    class InputSerializer(serializers.Serializer):
        conversation_id = serializers.CharField(
            required=False,
            allow_null=True,
            allow_blank=True,
            help_text="Optional conversation id previously created via the integrations conversation endpoint. Use to continue the same OpenAI conversation.",
        )
        input = serializers.CharField(
            required=True,
            allow_blank=False,
            help_text="Text to send to the assistant prompting the document search. E.g. 'List documents matching contract 2024 for company X'.",
        )

    class OutputSerializer(serializers.Serializer):
        response_text = serializers.CharField(
            help_text="Assistant textual response (string)"
        )
        documents_urls = serializers.DictField(
            child=serializers.CharField(),
            help_text="Mapping of document key -> presigned URL returned for each discovered document",
        )

    @extend_schema(
        summary="Conducts documentary research",
        description=(
            "Receives a text input that describes the document search and optionally "
            "a `conversation_id` to maintain context between calls. Returns the assistant's response text "
            "and a `documents_urls` dictionary with document keys and presigned URLs for download."
        ),
        request=InputSerializer,
        responses={200: OutputSerializer},
    )
    def post(self, request):
        request_id = str(uuid4())[:8]
        request_started_at = perf_counter()

        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        prompt = serializer.validated_data["input"]
        conversation_id = serializer.validated_data.get("conversation_id")
        integration_client = getattr(request.auth, "client", None)
        request_context = build_ricerca_documentale_request_context(
            prompt=prompt,
            integration_client=integration_client,
        )

        logger.info(
            "[ricerca_documentale][%s] request_started conversation_id=%s prompt_length=%s client=%s bucket=%s",
            request_id,
            conversation_id or "<new>",
            request_context.prompt_length,
            request_context.client_name or "<fallback>",
            request_context.bucket_name or "<empty>",
        )
        logger.info(
            "[ricerca_documentale][%s] intent_detected intent_type=%s confidence=%s matched_signals=%s primary_tool=%s prefer_preview_only=%s max_documents_to_open=%s group_by=%s",
            request_id,
            request_context.intent_classification.intent_type,
            request_context.intent_classification.confidence,
            ",".join(request_context.intent_classification.matched_signals) or "<none>",
            request_context.retrieval_strategy.primary_tool,
            request_context.retrieval_strategy.prefer_preview_only,
            request_context.retrieval_strategy.max_documents_to_open,
            request_context.retrieval_strategy.group_by or "<none>",
        )
        logger.info(
            "[ricerca_documentale][%s] model_input_prepared original_prompt_length=%s model_input_length=%s",
            request_id,
            len(prompt or ""),
            len(request_context.model_input or ""),
        )
        logger.info(
            "[ricerca_documentale][%s] presearch_completed candidates_count=%s customer_code=%s",
            request_id,
            len(request_context.presearch_candidates),
            request_context.customer_code or "<empty>",
        )
        logger.info(
            "[ricerca_documentale][%s] related_approval_candidates_completed candidates_count=%s",
            request_id,
            len(request_context.related_approval_candidates),
        )
        if request_context.presearch_candidates:
            primary_candidate = request_context.presearch_candidates[0]
            logger.info(
                "[ricerca_documentale][%s] presearch_primary_candidate filename=%s document_date=%s key=%s",
                request_id,
                getattr(primary_candidate, "filename", "") or "<empty>",
                getattr(primary_candidate, "document_date", "") or "<empty>",
                getattr(primary_candidate, "key", "") or "<empty>",
            )
            logger.info(
                "[ricerca_documentale][%s] presearch_candidates_ordered filenames=%s",
                request_id,
                " | ".join(
                    (
                        f"{getattr(candidate, 'filename', '') or '<empty>'}"
                        f"@{getattr(candidate, 'document_date', '') or '<empty>'}"
                    )
                    for candidate in request_context.presearch_candidates[:5]
                ),
            )
        if request_context.related_approval_candidates:
            logger.info(
                "[ricerca_documentale][%s] related_approval_candidates filenames=%s",
                request_id,
                " | ".join(
                    (
                        f"{getattr(candidate, 'filename', '') or '<empty>'}"
                        f"@{getattr(candidate, 'document_date', '') or '<empty>'}"
                    )
                    for candidate in request_context.related_approval_candidates[:2]
                ),
            )

        thread_started_at = perf_counter()
        with transaction.atomic():
            if conversation_id:
                assistant_thread = AssistantThread.objects.filter(
                    thread_id=conversation_id
                ).first()
                if not assistant_thread:
                    assistant_thread = AssistantThread.objects.create(
                        thread_id=conversation_id,
                        active=True,
                    )
            else:
                try:
                    conversation_openai = client.conversations.create()
                except Exception:
                    conversation_openai = None

                assistant_thread = AssistantThread.objects.create(
                    thread_id=conversation_openai.id if conversation_openai else "",
                    active=True,
                )

        thread_duration_ms = round((perf_counter() - thread_started_at) * 1000, 2)
        logger.info(
            "[ricerca_documentale][%s] thread_ready thread_id=%s duration_ms=%s",
            request_id,
            assistant_thread.thread_id or "<empty>",
            thread_duration_ms,
        )

        openai_started_at = perf_counter()
        try:
            response = client.responses.create(
                prompt={"id": settings.OPENAI_PROMPT_ID_RICERCA_DOCUMENTALE},
                input=request_context.model_input,
                conversation=assistant_thread.thread_id or None,
                tools=[
                    build_ricerca_documentale_mcp_tool(
                        mcp_token=request_context.mcp_token
                    )
                ],
                store=True,
                timeout=900,
            )
        except Exception:
            total_duration_ms = round((perf_counter() - request_started_at) * 1000, 2)
            logger.exception(
                "[ricerca_documentale][%s] openai_request_failed duration_ms=%s",
                request_id,
                total_duration_ms,
            )
            return Response(
                {"error": "Erro ao chamar o servico de respostas externo."},
                status=502,
            )

        openai_duration_ms = round((perf_counter() - openai_started_at) * 1000, 2)
        logger.info(
            "[ricerca_documentale][%s] openai_response_received duration_ms=%s",
            request_id,
            openai_duration_ms,
        )

        try:
            response_payload = extract_ricerca_documentale_response_payload(response)
        except Exception:
            logger.exception(
                "[ricerca_documentale][%s] response_parse_failed",
                request_id,
            )
            response_payload = None

        response_text = response_payload.response_text if response_payload else ""
        response_keys = response_payload.response_keys if response_payload else []
        raw_output_length = (
            response_payload.raw_output_length if response_payload else 0
        )

        documents_urls = {}
        presign_started_at = perf_counter()
        if response_keys:
            try:
                documents_urls = get_presigned_urls_for_document_keys(
                    response_keys,
                    customer_code=(request_context.customer_code or None),
                    fallback_bucket=request_context.bucket_name,
                )
            except Exception:
                logger.exception(
                    "[ricerca_documentale][%s] presigned_url_generation_failed keys_count=%s",
                    request_id,
                    len(response_keys),
                )
                documents_urls = {}
        presign_duration_ms = round((perf_counter() - presign_started_at) * 1000, 2)

        total_duration_ms = round((perf_counter() - request_started_at) * 1000, 2)
        logger.info(
            "[ricerca_documentale][%s] request_completed intent_type=%s total_duration_ms=%s openai_duration_ms=%s presign_duration_ms=%s raw_output_length=%s response_text_length=%s response_keys_count=%s documents_urls_count=%s model_input_length=%s",
            request_id,
            request_context.intent_classification.intent_type,
            total_duration_ms,
            openai_duration_ms,
            presign_duration_ms,
            raw_output_length,
            len(response_text or ""),
            len(response_keys),
            len(documents_urls),
            len(request_context.model_input or ""),
        )

        record_integration_ricerca_documentale_usage(
            auth=request.auth,
            integration_client=integration_client,
            request_id=request_id,
            conversation_id=assistant_thread.thread_id or "",
            prompt=prompt,
            request_context=request_context,
            response_text=response_text,
            documents_count=len(documents_urls),
            metadata={
                "openai_duration_ms": openai_duration_ms,
                "presign_duration_ms": presign_duration_ms,
                "total_duration_ms": total_duration_ms,
                "response_keys_count": len(response_keys),
            },
        )

        return Response(
            {"response_text": response_text, "documents_urls": documents_urls}
        )
