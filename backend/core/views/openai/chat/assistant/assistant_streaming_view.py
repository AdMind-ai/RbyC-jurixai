from django.conf import settings
from core.models.usage import UsageTool
from core.services.usage_tracking import UsageTrackingService
from core.utils.common import safe_load_json
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from openai import OpenAI
from rest_framework import serializers
import logging
from typing import Any, Dict, Optional

# Functions
from core.utils.assistants import *
from core.utils.s3_utils import get_presigned_urls

from core.models.openai_chat_models import ChatConversation, ChatMessage
from core.models.assistant_thread_model import AssistantThread
from django.db import transaction

client = OpenAI(api_key=settings.OPENAI_KEY)
logger = logging.getLogger(__name__)

class AssistantMessageSerializer(serializers.Serializer):
    thread_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    content = serializers.CharField(required=True, allow_blank=False)

class AssistantStreamingView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AssistantMessageSerializer


    # -----------------------------------------------------
    #            STREAMING OPENAI + MCP
    # -----------------------------------------------------
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        prompt = serializer.validated_data["content"]
        thread_id = serializer.validated_data["thread_id"]

        # ------------------------------------------
        #   SETUP CONVERSA
        # ------------------------------------------
        with transaction.atomic():
            if thread_id:
                assistant_thread = AssistantThread.objects.filter(thread_id=thread_id).first()
                if not assistant_thread:
                    conversation_openai = client.conversations.create()
                    assistant_thread = AssistantThread.objects.create(
                        thread_id=conversation_openai.id, active=True
                    )
            else:
                conversation_openai = client.conversations.create()
                assistant_thread = AssistantThread.objects.create(
                    thread_id=conversation_openai.id, active=True
                )

            if assistant_thread.conversation:
                conversation = assistant_thread.conversation
            else:
                user = request.user
                ChatConversation.objects.filter(user=user, is_new=True).delete()
                conversation = ChatConversation.objects.create(
                    user=user, name="New Chat", is_new=True
                )
                assistant_thread.conversation = conversation
                assistant_thread.save(update_fields=["conversation"])

        ChatMessage.objects.create(
            conversation=conversation, content=prompt, is_user=True
        )

        # --------------------------------------------------------
        #       STREAM DE RESPOSTA DA OPENAI
        # --------------------------------------------------------
        try:
            response = client.responses.create(
                prompt={"id": settings.OPENAI_PROMPT_ID_RICERCA_DOCUMENTALE},
                input=prompt,
                conversation=assistant_thread.thread_id,
                tools=[{
                    "type": "mcp",
                    "server_label": 'rbyc',
                    "server_description": "Ferramenta para listar documentos do S3",
                    "server_url": settings.MCP_SERVER_URL,
                    "allowed_tools": ["list_documents", "get_document"],
                    "require_approval": "never",
                }],
                store=True,
                timeout=900,
            )
        except Exception as e:
            logger.exception("Erro ao chamar OpenAI Responses API: %s", e)
            return Response({"error": "Erro ao chamar o serviço de respostas externo."}, status=502)

        # Log raw output_text for debugging
        try:
            raw_output = getattr(response, 'output_text', None)
        except Exception:
            raw_output = str(response)

        logger.debug("RESPOSTA ASSISTANT (raw): %s", raw_output)

        # safe_load_json may return dict or other types — handle both robustly
        try:
            jsonRes: Optional[Any] = safe_load_json(raw_output)
        except Exception:
            logger.exception("Falha ao parsear response.output_text como JSON; usando fallback de texto cru.")
            jsonRes = None

        # Derive the response text and keys in a fault-tolerant way
        response_text = ''
        response_keys = []

        if isinstance(jsonRes, dict):
            # common case: assistant returned a dict
            response_text = (
                jsonRes.get('response')
                or jsonRes.get('output_text')
                or jsonRes.get('text')
                or raw_output
            )

            # If the assistant provided an explicit 'keys' list, use it.
            if 'keys' in jsonRes and isinstance(jsonRes['keys'], (list, tuple)):
                response_keys = list(jsonRes['keys'])
            else:
                # fallback: use dict keys (may include other fields)
                try:
                    response_keys = list(jsonRes.keys())
                except Exception:
                    response_keys = []

        elif jsonRes is None:
            response_text = raw_output or ''
            response_keys = []
        else:
            # object-like response (previous code path)
            response_text = getattr(jsonRes, 'response', None) or getattr(jsonRes, 'output_text', None) or str(jsonRes)
            try:
                response_keys = list(getattr(jsonRes, 'keys', [])())
            except Exception:
                response_keys = []

        # Ensure response_text is always a string (avoid saving None to DB)
        if response_text is None:
            response_text = ''
        elif not isinstance(response_text, str):
            response_text = str(response_text)

        logger.debug("JSON RESPOSTA ASSISTANT (parsed): %s", response_text)
        logger.debug("JSON RESPOSTA ASSISTANT keys: %s", response_keys)

        # Attempt to fetch presigned URLs for any document-like keys returned by the assistant
        documents_urls = {}
        if response_keys:
            try:
                documents_urls = get_presigned_urls(response_keys)
            except Exception as e:
                logger.exception("Erro ao recuperar URLs S3: %s", e)

        # Normalize documents_urls into a list suitable for ChatMessage.citations (JSONField)
        # Each item: { id, title, url, type }
        citations_list = []
        try:
            for idx, (key, url) in enumerate((documents_urls or {}).items()):
                parts = str(key).split('/') if key else [str(key)]
                filename = parts[-1] if parts else str(key)
                ext_match = None
                try:
                    import re

                    m = re.search(r"\.([0-9a-zA-Z]+)(?:\?|$)", filename)
                    ext_match = m.group(1).lower() if m else ''
                except Exception:
                    ext_match = ''

                citations_list.append({
                    'id': f"{idx}-{filename}",
                    'title': filename,
                    'url': url,
                    'type': ext_match,
                })
        except Exception:
            logger.exception("Erro ao normalizar documents_urls para citations_list")

        # Persist message (store the plain text that will be shown to users) along with citations
        ChatMessage.objects.create(
            conversation=conversation,
            content=response_text,
            is_user=False,
            citations=citations_list,
        )
        
        # Registra meio crédito por request (1 uso a cada duas requisições)
        UsageTrackingService.record_usage_event(
            user=request.user,
            tool=UsageTool.RICERCA_DOCUMENTALE,
            quantity=1/2,
            company=getattr(request.user, "company", None),
            metadata={
                "conversation_id": conversation.id
            },
        )

        res = {
            "response_text": response_text,
            "documents_urls": documents_urls,
        }

        return Response(res)
