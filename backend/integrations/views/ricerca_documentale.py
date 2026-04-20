import logging
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
from core.utils.openai_client import client
from core.utils.s3_utils import get_presigned_urls
from integrations.authentication import APIKeyAuthentication
from integrations.permissions import HasValidAPIKey


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
        prompt_length = len(prompt or "")
        integration_client = getattr(request.auth, "client", None)
        bucket_name = (
            getattr(integration_client, "bucket_name", None)
            or getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
        )
        client_name = getattr(integration_client, "client_name", None)

        logger.info(
            "[ricerca_documentale][%s] request_started conversation_id=%s prompt_length=%s client=%s bucket=%s",
            request_id,
            conversation_id or "<new>",
            prompt_length,
            client_name or "<fallback>",
            bucket_name or "<empty>",
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
                input=prompt,
                conversation=assistant_thread.thread_id or None,
                tools=[
                    {
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
            "[ricerca_documentale][%s] request_completed total_duration_ms=%s openai_duration_ms=%s presign_duration_ms=%s raw_output_length=%s response_text_length=%s response_keys_count=%s documents_urls_count=%s",
            request_id,
            total_duration_ms,
            openai_duration_ms,
            presign_duration_ms,
            raw_output_length,
            len(response_text or ""),
            len(response_keys),
            len(documents_urls),
        )

        return Response(
            {"response_text": response_text, "documents_urls": documents_urls}
        )
