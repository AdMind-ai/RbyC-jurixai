from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from integrations.authentication import APIKeyAuthentication
from integrations.permissions import HasValidAPIKey

from rest_framework import serializers
from django.db import transaction
from django.conf import settings
from core.utils.openai_client import client
from core.models.assistant_thread_model import AssistantThread
from core.utils.s3_utils import get_presigned_urls
from typing import Any, Optional


@extend_schema(
    summary="Responsável por fornecer um endpoint para a pesquisa documental",
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
        response_text = serializers.CharField(help_text="Assistant textual response (string)")
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
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        prompt = serializer.validated_data["input"]
        conversation_id = serializer.validated_data.get("conversation_id")

        # Create or reuse AssistantThread (no user linkage for integrations)
        with transaction.atomic():
            if conversation_id:
                assistant_thread = AssistantThread.objects.filter(thread_id=conversation_id).first()
                if not assistant_thread:
                    assistant_thread = AssistantThread.objects.create(thread_id=conversation_id, active=True)
            else:
                try:
                    conversation_openai = client.conversations.create()
                except Exception:
                    conversation_openai = None

                assistant_thread = AssistantThread.objects.create(thread_id=conversation_openai.id if conversation_openai else "", active=True)

        # Call OpenAI Responses API
        try:
            response = client.responses.create(
                prompt={"id": settings.OPENAI_PROMPT_ID_RICERCA_DOCUMENTALE},
                input=prompt,
                conversation=assistant_thread.thread_id or None,
                tools=[{
                    "type": "mcp",
                    "server_label": 'rbyc',
                    "server_description": "Ferramenta para listar documentos do S3",
                    "server_url": "https://mcp-server-ricerca-rbyc.onrender.com/sse",
                    "allowed_tools": ["list_documents", "get_document"],
                    "require_approval": "never",
                }],
                store=True,
                timeout=900,
            )
        except Exception:
            return Response({"error": "Erro ao chamar o serviço de respostas externo."}, status=502)

        # extract output_text
        try:
            raw_output = getattr(response, 'output_text', None)
        except Exception:
            raw_output = str(response)

        # attempt to parse JSON-like output
        from core.utils.common import safe_load_json
        try:
            jsonRes: Optional[Any] = safe_load_json(raw_output)
        except Exception:
            jsonRes = None

        response_text = ''
        response_keys = []

        if isinstance(jsonRes, dict):
            response_text = (
                jsonRes.get('response')
                or jsonRes.get('output_text')
                or jsonRes.get('text')
                or raw_output
            )
            if 'keys' in jsonRes and isinstance(jsonRes['keys'], (list, tuple)):
                response_keys = list(jsonRes['keys'])
            else:
                try:
                    response_keys = list(jsonRes.keys())
                except Exception:
                    response_keys = []
        elif jsonRes is None:
            response_text = raw_output or ''
        else:
            response_text = getattr(jsonRes, 'response', None) or getattr(jsonRes, 'output_text', None) or str(jsonRes)

        if response_text is None:
            response_text = ''
        elif not isinstance(response_text, str):
            response_text = str(response_text)

        # fetch presigned urls for keys if present
        documents_urls = {}
        if response_keys:
            try:
                documents_urls = get_presigned_urls(response_keys)
            except Exception:
                documents_urls = {}

        return Response({"response_text": response_text, "documents_urls": documents_urls})
