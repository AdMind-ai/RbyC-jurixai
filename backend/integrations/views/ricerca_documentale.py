import logging
from collections.abc import Mapping, Sequence
from time import perf_counter
from typing import Any, Optional
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models.assistant_thread_model import AssistantThread
from core.services.document_retrieval.intent_classifier import (
    classify_document_search_intent,
)
from core.services.document_retrieval.prompt_context import (
    build_document_search_input,
)
from core.services.document_retrieval.retrieval_strategies import (
    get_retrieval_strategy,
)
from core.utils.openai_client import client
from core.utils.s3_utils import get_presigned_urls
from integrations.authentication import APIKeyAuthentication
from integrations.permissions import HasValidAPIKey
from integrations.services.mcp_auth import build_mcp_access_token


logger = logging.getLogger(__name__)


def _looks_like_document_key(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip()
    if not normalized or normalized.endswith("/"):
        return False
    return "/" in normalized or "." in normalized


def _coerce_to_plain_data(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)

    for method_name in ("model_dump", "dict"):
        method = getattr(value, method_name, None)
        if callable(method):
            try:
                return method()
            except Exception:
                continue

    if hasattr(value, "__dict__"):
        try:
            return vars(value)
        except Exception:
            return value
    return value


def _collect_document_keys_from_payload(payload: Any) -> list[str]:
    from core.utils.common import safe_load_json

    collected: list[str] = []
    seen_ids: set[int] = set()

    def visit(node: Any) -> None:
        node = _coerce_to_plain_data(node)
        node_id = id(node)
        if node_id in seen_ids:
            return
        seen_ids.add(node_id)

        if node is None:
            return

        if isinstance(node, str):
            text = node.strip()
            if not text:
                return
            parsed = None
            if text.startswith("{") or text.startswith("["):
                try:
                    parsed = safe_load_json(text)
                except Exception:
                    parsed = None
            if parsed not in (None, text):
                visit(parsed)
            return

        if isinstance(node, Mapping):
            keys_value = node.get("keys")
            if isinstance(keys_value, (list, tuple)):
                for item in keys_value:
                    if _looks_like_document_key(item):
                        collected.append(item.strip())

            key_value = node.get("key")
            if _looks_like_document_key(key_value):
                collected.append(key_value.strip())

            path_value = node.get("path")
            if _looks_like_document_key(path_value):
                collected.append(path_value.strip())

            output_value = node.get("output")
            if output_value is not None:
                visit(output_value)

            content_value = node.get("content")
            if content_value is not None:
                visit(content_value)

            for child in node.values():
                if child in {keys_value, key_value, path_value, output_value, content_value}:
                    continue
                visit(child)
            return

        if isinstance(node, Sequence) and not isinstance(node, (str, bytes, bytearray)):
            for item in node:
                visit(item)

    visit(payload)

    deduped: list[str] = []
    seen_keys: set[str] = set()
    for item in collected:
        if item not in seen_keys:
            seen_keys.add(item)
            deduped.append(item)
    return deduped


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
        prompt_length = len(prompt or "")
        intent_classification = classify_document_search_intent(prompt)
        retrieval_strategy = get_retrieval_strategy(
            intent_classification.intent_type
        )
        model_input = build_document_search_input(
            prompt,
            intent_classification,
            retrieval_strategy,
        )
        integration_client = getattr(request.auth, "client", None)
        bucket_name = (
            getattr(integration_client, "bucket_name", None)
            or getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
        )
        client_name = getattr(integration_client, "client_name", None)
        mcp_token = (
            build_mcp_access_token(integration_client)
            if integration_client is not None
            else None
        )

        logger.info(
            "[ricerca_documentale][%s] request_started conversation_id=%s prompt_length=%s client=%s bucket=%s",
            request_id,
            conversation_id or "<new>",
            prompt_length,
            client_name or "<fallback>",
            bucket_name or "<empty>",
        )
        logger.info(
            "[ricerca_documentale][%s] intent_detected intent_type=%s confidence=%s matched_signals=%s primary_tool=%s prefer_preview_only=%s max_documents_to_open=%s group_by=%s",
            request_id,
            intent_classification.intent_type,
            intent_classification.confidence,
            ",".join(intent_classification.matched_signals) or "<none>",
            retrieval_strategy.primary_tool,
            retrieval_strategy.prefer_preview_only,
            retrieval_strategy.max_documents_to_open,
            retrieval_strategy.group_by or "<none>",
        )
        logger.info(
            "[ricerca_documentale][%s] model_input_prepared original_prompt_length=%s model_input_length=%s",
            request_id,
            len(prompt or ""),
            len(model_input or ""),
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
                conversation=assistant_thread.thread_id or None,
                tools=[mcp_tool],
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
            raw_output = getattr(response, "output_text", None)
        except Exception:
            raw_output = str(response)
        raw_output_length = len(raw_output or "")

        from core.utils.common import safe_load_json

        try:
            json_res: Optional[Any] = safe_load_json(raw_output)
        except Exception:
            logger.exception(
                "[ricerca_documentale][%s] response_parse_failed raw_output_length=%s",
                request_id,
                raw_output_length,
            )
            json_res = None

        response_text = ""
        response_keys = []

        if isinstance(json_res, dict):
            response_text = (
                json_res.get("response")
                or json_res.get("output_text")
                or json_res.get("text")
                or raw_output
            )
            if "keys" in json_res and isinstance(json_res["keys"], (list, tuple)):
                response_keys = list(json_res["keys"])
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

        if not response_keys:
            try:
                response_keys = _collect_document_keys_from_payload(response)
            except Exception:
                logger.exception(
                    "[ricerca_documentale][%s] response_key_extraction_failed raw_output_length=%s",
                    request_id,
                    raw_output_length,
                )
                response_keys = []

        documents_urls = {}
        presign_started_at = perf_counter()
        if response_keys:
            try:
                documents_urls = get_presigned_urls(response_keys, bucket=bucket_name)
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
            intent_classification.intent_type,
            total_duration_ms,
            openai_duration_ms,
            presign_duration_ms,
            raw_output_length,
            len(response_text or ""),
            len(response_keys),
            len(documents_urls),
            len(model_input or ""),
        )

        return Response(
            {"response_text": response_text, "documents_urls": documents_urls}
        )
