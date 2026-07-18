from core.models.usage import UsageSubTool, UsageTool
from core.services.usage_tracking import UsageTrackingService
from core.models.assistant_thread_model import AssistantThread
from rest_framework.views import APIView
from django.http import StreamingHttpResponse
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import status, permissions
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from rest_framework_simplejwt.authentication import JWTAuthentication
from core.models.openai_chat_models import ChatConversation, ChatMessage
from core.serializers.openai_chat_serializers import MessageSerializer
from core.utils.openai_client import client, logger
import tiktoken
import base64
import mimetypes
from django.db import transaction


CHAT_ASSISTANT_MODEL = "gpt-5.6-terra"


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class OpenAISendMessageView(APIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    parser_classes = [FormParser, MultiPartParser, JSONParser]

    def post(self, request):
        user = request.user
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation_id = request.data.get('conversation_id')

        content = serializer.validated_data.get('content', '')
        file = serializer.validated_data.get('file', None)
        model = request.data.get('model', CHAT_ASSISTANT_MODEL)
        web_search_enabled = _parse_bool(request.data.get('web_search_enabled'))

        if model != CHAT_ASSISTANT_MODEL:
            raise ValidationError(
                f"Unsupported model for Chat Assistant. Use {CHAT_ASSISTANT_MODEL}."
            )

        # logger.debug(
        #     f"Received data - Content: {content}, Model: {model}, User: {user}, conversation_id: {conversation_id}, file: {file}")

        # model_config_map = {
        #     'gpt-5': ('o200k_base', 300000, 100000),
        # }

        # encoding_name, context_window, max_output_tokens = model_config_map.get(
        #     model, ('o200k_base', 120000, 16000))

        # max_input_tokens = context_window - max_output_tokens

        with transaction.atomic():
            assistant_thread = None

            if conversation_id:
                assistant_thread = AssistantThread.objects.filter(thread_id=conversation_id).first()
                if not assistant_thread:
                    # thread_id inválido → criar novo registro
                    assistant_thread = AssistantThread.objects.create(thread_id=conversation_id, active=True)
            else:
                # cria thread local, id será preenchido depois
                conversation_openai = client.conversations.create()
                assistant_thread = AssistantThread.objects.create(thread_id=conversation_openai.id, active=True)
                conversation_id = conversation_openai.id
            
            # cria ou reaproveita conversa local (ChatConversation)
            if assistant_thread and assistant_thread.conversation:
                conversation = assistant_thread.conversation
            else:
                # cria nova conversa local
                user = request.user
                ChatConversation.objects.filter(user=user, is_new=True).delete()
                conversation = ChatConversation.objects.create(
                    user=user,
                    name="New Chat",
                    is_new=True
                )
                assistant_thread.conversation = conversation
                assistant_thread.save(update_fields=["conversation"])

        conversation_id = assistant_thread.thread_id if assistant_thread else conversation_id

        # salva a mensagem do usuário
        ChatMessage.objects.create(
            conversation=conversation,
            content=content,
            is_user=True
        )

        user_message_content = [] if file else content

        if file:
            user_message_content = [{"type": "input_text", "text": content}]
            file_content = file.read()
            file_type, _ = mimetypes.guess_type(file.name)
            file_base64 = base64.b64encode(file_content).decode('utf-8')

            if 'image' in file.content_type:
                user_message_content.append(
                    {"type": "input_image",
                        "image_url": f"data:{file_type};base64,{file_base64}"}
                )
            else:
                user_message_content.append(
                    {"type": "input_file",
                        "filename": file.name,
                        "file_data": f"data:{file_type};base64,{file_base64}"}
                )

        def event_stream():
            full_ai_message = ""
            try:
                response_kwargs = {
                    "model": model,
                    "input": [
                        {
                            "role": "user",
                            "content": user_message_content
                        },
                    ],
                    "conversation": conversation_id,
                    "store": True,
                    "stream": True,
                    "reasoning": {
                        "effort": "medium"
                    },
                    "timeout": 600,
                }

                if web_search_enabled:
                    response_kwargs["tools"] = [{"type": "web_search_preview"}]
                    response_kwargs["include"] = [
                        "reasoning.encrypted_content",
                        "web_search_call.action.sources",
                    ]
                else:
                    response_kwargs["include"] = ["reasoning.encrypted_content"]

                response = client.responses.create(
                    **response_kwargs,
                )
                for event in response:
                    if getattr(event, 'type', None) == 'response.output_text.delta':
                        delta_content = event.delta
                        if delta_content:
                            full_ai_message += delta_content
                            print(delta_content, end='')
                            yield delta_content

            except Exception as e:
                logger.error("Erro ao fazer streaming: %s", e)
            else:
                ChatMessage.objects.create(
                    conversation=conversation,
                    content=full_ai_message,
                    is_user=False
                )
                
                UsageTrackingService.record_usage_event(
                    user=request.user,
                    tool=UsageTool.CHAT_ASSISTANT,
                    sub_tool=UsageSubTool.GPT_5_6_TERRA,
                    quantity=1,
                    company=getattr(request.user, "company", None),
                    metadata={
                        "conversation_id": conversation.id,
                        "message_length": len(full_ai_message),
                        "has_file": bool(file),
                        "model": model,
                        "web_search_enabled": web_search_enabled,
                    },
                )

        return StreamingHttpResponse(event_stream(), content_type='text/event-stream')


def num_tokens_from_string(string: str, encoding_name: str) -> int:
    encoding = tiktoken.get_encoding(encoding_name)
    return len(encoding.encode(string))


def manage_history_tokens(history, new_message, encoding_name, max_input_tokens):
    def ensure_string(msg_content):
        if isinstance(msg_content, list):
            return " ".join(
                item.get("text", "") if isinstance(
                    item, dict) and "text" in item else str(item)
                for item in msg_content
            )
        elif isinstance(msg_content, dict):
            return " ".join(
                f"{k}: {v}" for k, v in msg_content.items()
                if isinstance(v, str)
            )
        elif isinstance(msg_content, str):
            return msg_content
        else:
            return str(msg_content)

    current_tokens = sum(num_tokens_from_string(
        ensure_string(msg['content']), encoding_name) for msg in history)
    current_tokens += num_tokens_from_string(
        ensure_string(new_message), encoding_name)

    while current_tokens > max_input_tokens and len(history) > 0:
        oldest_message = history.pop(0)
        current_tokens -= num_tokens_from_string(
            ensure_string(oldest_message['content']), encoding_name)

    return history, current_tokens


def encode_image_to_base64(file_path):
    with open(file_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
