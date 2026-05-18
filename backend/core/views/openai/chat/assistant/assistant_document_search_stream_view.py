import logging
from time import perf_counter
from typing import Any, Optional

from django.conf import settings
from django.db import transaction
from django.http import StreamingHttpResponse
from openai import OpenAI
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.models.assistant_thread_model import AssistantThread
from core.models.openai_chat_models import ChatConversation, ChatMessage
from core.models.usage import UsageTool
from core.services.document_retrieval.intent_classifier import (
    classify_document_search_intent,
)
from core.services.document_retrieval.prompt_context import (
    build_document_search_input,
)
from core.services.document_retrieval.presearch import (
    build_presearch_candidates,
    build_related_approval_candidates,
)
from core.services.document_retrieval.retrieval_strategies import (
    get_retrieval_strategy,
)
from core.services.document_retrieval.streaming import (
    PHASE_COMPLETED,
    PHASE_COMPACTING_EVIDENCE,
    PHASE_ERROR,
    PHASE_INTENT_DETECTION,
    PHASE_PLANNING,
    PHASE_READING,
    PHASE_SEARCHING,
    PHASE_SYNTHESIZING,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_IN_PROGRESS,
    DocumentSearchNarrationService,
    build_execution_event,
    encode_sse_event,
    iter_text_deltas,
)
from core.services.usage_tracking import UsageTrackingService
from core.utils.common import safe_load_json
from core.utils.s3_utils import get_presigned_urls_for_document_keys
from integrations.models import IntegrationClient
from integrations.services.mcp_auth import build_mcp_access_token


client = OpenAI(api_key=settings.OPENAI_KEY)
logger = logging.getLogger(__name__)


class AssistantDocumentSearchStreamSerializer(serializers.Serializer):
    thread_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    content = serializers.CharField(required=True, allow_blank=False)


class AssistantDocumentSearchStreamView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AssistantDocumentSearchStreamSerializer

    def post(self, request, *args, **kwargs):
        request_started_at = perf_counter()
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        prompt = serializer.validated_data["content"]
        thread_id = serializer.validated_data.get("thread_id")
        intent_classification = classify_document_search_intent(prompt)
        retrieval_strategy = get_retrieval_strategy(
            intent_classification.intent_type
        )
        presearch_candidates = build_presearch_candidates(
            user_input=prompt,
            intent_classification=intent_classification,
            retrieval_strategy=retrieval_strategy,
            customer_code="default",
        )
        related_approval_candidates = build_related_approval_candidates(
            user_input=prompt,
            primary_candidate=presearch_candidates[0] if presearch_candidates else None,
            customer_code="default",
        )
        model_input = build_document_search_input(
            prompt,
            intent_classification,
            retrieval_strategy,
            presearch_candidates=presearch_candidates,
            related_approval_candidates=related_approval_candidates,
        )
        integration_client = IntegrationClient.objects.filter(
            customer_code="default",
            active=True,
        ).first()
        mcp_token = (
            build_mcp_access_token(integration_client)
            if integration_client is not None
            else None
        )

        with transaction.atomic():
            if thread_id:
                assistant_thread = AssistantThread.objects.filter(
                    thread_id=thread_id
                ).first()
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

        narration_service = DocumentSearchNarrationService()
        final_answer_model = getattr(
            settings,
            "DOCUMENT_SEARCH_STREAM_FINAL_MODEL",
            "gpt-5.4-mini",
        )

        def event_stream():
            emitted_events = []
            raw_output_chunks = []
            response_text = ""
            response_keys = []
            documents_urls = {}
            emitted_phases: set[tuple[str, str]] = set()

            def emit_execution_event(phase: str, status: str, payload: dict[str, Any], narrate: bool = True):
                phase_key = (phase, status)
                if phase_key in emitted_phases and status == STATUS_IN_PROGRESS:
                    return

                event = build_execution_event(
                    request_id=assistant_thread.thread_id or "stream",
                    phase=phase,
                    status=status,
                    payload=payload,
                )
                emitted_events.append(event)
                emitted_phases.add(phase_key)
                yield encode_sse_event("execution_event", event.as_payload())

                if narrate:
                    narration = narration_service.build_narration_event(
                        request_id=assistant_thread.thread_id or "stream",
                        user_prompt=prompt,
                        execution_event=event,
                        previous_events=emitted_events[:-1],
                    )
                    yield encode_sse_event("narration_event", narration)

            try:
                logger.info(
                    "[assistant_document_search_stream] request_started thread_id=%s intent_type=%s model_input_length=%s presearch_candidates=%s related_approval_candidates=%s",
                    assistant_thread.thread_id or "<empty>",
                    intent_classification.intent_type,
                    len(model_input or ""),
                    len(presearch_candidates),
                    len(related_approval_candidates),
                )

                yield from emit_execution_event(
                    PHASE_INTENT_DETECTION,
                    STATUS_COMPLETED,
                    {
                        "intent_type": intent_classification.intent_type,
                        "confidence": intent_classification.confidence,
                    },
                )
                yield from emit_execution_event(
                    PHASE_PLANNING,
                    STATUS_COMPLETED,
                    {
                        "primary_tool": retrieval_strategy.primary_tool,
                        "group_by": retrieval_strategy.group_by or "",
                        "prefer_preview_only": retrieval_strategy.prefer_preview_only,
                    },
                )
                yield from emit_execution_event(
                    PHASE_SEARCHING,
                    STATUS_IN_PROGRESS,
                    {
                        "focus": ", ".join(intent_classification.matched_signals)
                        or prompt[:120],
                    },
                )

                mcp_tool = {
                    "type": "mcp",
                    "server_label": "rbyc",
                    "server_description": "Ferramenta para buscar documentos indexados, listar metadados e consultar trechos quando necessario",
                    "server_url": settings.MCP_SERVER_URL,
                    "allowed_tools": [
                        "search_documents",
                        "list_documents",
                        "get_document",
                    ],
                    "require_approval": "never",
                }
                if mcp_token:
                    mcp_tool["headers"] = {
                        "Authorization": f"Bearer {mcp_token}",
                    }

                response = client.responses.create(
                    prompt={"id": settings.OPENAI_PROMPT_ID_RICERCA_DOCUMENTALE},
                    input=model_input,
                    conversation=assistant_thread.thread_id,
                    tools=[mcp_tool],
                    store=True,
                    timeout=900,
                    stream=True,
                )

                emitted_reading = False
                emitted_compacting = False
                emitted_synthesizing = False

                for event in response:
                    event_type = getattr(event, "type", "") or ""

                    if event_type == "response.output_item.added":
                        item = getattr(event, "item", None)
                        item_type = getattr(item, "type", "") or ""
                        item_name = getattr(item, "name", "") or getattr(
                            item, "tool_name", ""
                        )
                        if "mcp" in item_type or "search" in item_name:
                            if not emitted_reading and "get_document" in item_name:
                                emitted_reading = True
                                yield from emit_execution_event(
                                    PHASE_READING,
                                    STATUS_IN_PROGRESS,
                                    {
                                        "document_role": "supporting_source",
                                        "document_family": "mixed",
                                        "tool_name": item_name,
                                    },
                                )
                            elif "search" in item_name or "list_documents" in item_name:
                                yield from emit_execution_event(
                                    PHASE_SEARCHING,
                                    STATUS_IN_PROGRESS,
                                    {
                                        "tool_name": item_name,
                                    },
                                    narrate=False,
                                )

                    if event_type == "response.output_text.delta":
                        delta_content = event.delta or ""
                        if delta_content:
                            raw_output_chunks.append(delta_content)
                            if not emitted_compacting:
                                emitted_compacting = True
                                yield from emit_execution_event(
                                    PHASE_COMPACTING_EVIDENCE,
                                    STATUS_IN_PROGRESS,
                                    {"grouping_key": retrieval_strategy.group_by or "document"},
                                )
                            if not emitted_synthesizing:
                                emitted_synthesizing = True
                                yield from emit_execution_event(
                                    PHASE_SYNTHESIZING,
                                    STATUS_IN_PROGRESS,
                                    {"evidence_ready": True},
                                )

                raw_output = "".join(raw_output_chunks)
                json_res: Optional[Any]
                try:
                    json_res = safe_load_json(raw_output)
                except Exception:
                    logger.exception(
                        "[assistant_document_search_stream] response_parse_failed raw_output_length=%s",
                        len(raw_output or ""),
                    )
                    json_res = None

                if isinstance(json_res, dict):
                    response_text = (
                        json_res.get("response")
                        or json_res.get("output_text")
                        or json_res.get("text")
                        or raw_output
                    )
                    if "keys" in json_res and isinstance(
                        json_res["keys"], (list, tuple)
                    ):
                        response_keys = list(json_res["keys"])
                    else:
                        try:
                            response_keys = list(json_res.keys())
                        except Exception:
                            response_keys = []
                elif json_res is None:
                    response_text = raw_output or ""
                else:
                    response_text = (
                        getattr(json_res, "response", None)
                        or getattr(json_res, "output_text", None)
                        or str(json_res)
                    )

                if response_text is None:
                    response_text = ""
                elif not isinstance(response_text, str):
                    response_text = str(response_text)

                if response_keys:
                    try:
                        documents_urls = get_presigned_urls_for_document_keys(
                            response_keys,
                            customer_code="default",
                            fallback_bucket=(
                                getattr(integration_client, "bucket_name", None)
                                or getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
                            ),
                        )
                    except Exception:
                        logger.exception(
                            "[assistant_document_search_stream] presigned_url_generation_failed keys_count=%s",
                            len(response_keys),
                        )
                        documents_urls = {}

                final_response_text = ""

                yield from emit_execution_event(
                    PHASE_COMPLETED,
                    STATUS_COMPLETED,
                    {
                        "response_text_length": len(response_text or ""),
                        "documents_urls_count": len(documents_urls),
                    },
                    narrate=False,
                )
                yield encode_sse_event(
                    "answer_started",
                    {
                        "type": "answer_started",
                        "request_id": assistant_thread.thread_id or "stream",
                    },
                )

                try:
                    final_answer_response = client.responses.create(
                        model=final_answer_model,
                        input=(
                            "Sei un assistente che riscrive una risposta documentale "
                            "per mostrarla in chat all'utente finale. "
                            "Mantieni fedelmente i contenuti sostanziali della bozza, "
                            "senza aggiungere nuove informazioni o interpretazioni. "
                            "Scrivi in italiano chiaro e naturale. "
                            "Restituisci solo il testo finale della risposta.\n\n"
                            f"Domanda utente:\n{prompt}\n\n"
                            f"Bozza di risposta:\n{response_text}"
                        ),
                        stream=True,
                        timeout=120,
                    )

                    for event in final_answer_response:
                        if getattr(event, "type", "") != "response.output_text.delta":
                            continue
                        delta_chunk = event.delta or ""
                        if not delta_chunk:
                            continue
                        final_response_text += delta_chunk
                        yield encode_sse_event(
                            "answer_delta",
                            {
                                "type": "answer_delta",
                                "request_id": assistant_thread.thread_id or "stream",
                                "delta": delta_chunk,
                            },
                        )
                except Exception:
                    logger.exception(
                        "[assistant_document_search_stream] final_answer_stream_failed thread_id=%s model=%s",
                        assistant_thread.thread_id or "<empty>",
                        final_answer_model,
                    )
                    final_response_text = ""

                if not final_response_text.strip():
                    final_response_text = response_text
                    for delta_chunk in iter_text_deltas(final_response_text):
                        yield encode_sse_event(
                            "answer_delta",
                            {
                                "type": "answer_delta",
                                "request_id": assistant_thread.thread_id or "stream",
                                "delta": delta_chunk,
                            },
                        )

                ChatMessage.objects.create(
                    conversation=conversation,
                    content=final_response_text,
                    is_user=False,
                )

                UsageTrackingService.record_usage_event(
                    user=request.user,
                    tool=UsageTool.RICERCA_DOCUMENTALE,
                    quantity=1,
                    company=getattr(request.user, "company", None),
                    metadata={"conversation_id": conversation.id},
                )

                yield encode_sse_event(
                    "answer_completed",
                    {
                        "type": "answer_completed",
                        "request_id": assistant_thread.thread_id or "stream",
                        "response_text": final_response_text,
                        "documents_urls": documents_urls,
                    },
                )

                total_duration_ms = round(
                    (perf_counter() - request_started_at) * 1000, 2
                )
                logger.info(
                    "[assistant_document_search_stream] request_completed intent_type=%s total_duration_ms=%s response_text_length=%s documents_urls_count=%s model_input_length=%s",
                    intent_classification.intent_type,
                    total_duration_ms,
                    len(final_response_text or ""),
                    len(documents_urls),
                    len(model_input or ""),
                )
            except Exception as exc:
                logger.exception(
                    "[assistant_document_search_stream] stream_failed thread_id=%s",
                    assistant_thread.thread_id or "<empty>",
                )
                yield from emit_execution_event(
                    PHASE_ERROR,
                    STATUS_FAILED,
                    {"message": str(exc)},
                    narrate=False,
                )
                yield encode_sse_event(
                    "error",
                    {
                        "type": "error",
                        "request_id": assistant_thread.thread_id or "stream",
                        "message": "Erro ao executar o streaming da pesquisa documental.",
                    },
                )

        response = StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
