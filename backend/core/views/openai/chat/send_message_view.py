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
import json
import base64
import mimetypes


class OpenAISendMessageView(APIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    parser_classes = [FormParser, MultiPartParser, JSONParser]

    def post(self, request):
        user = request.user
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation_instance = serializer.validated_data.get('conversation')
        conversation_id = request.data.get('conversation_id')

        content = serializer.validated_data.get('content', '')
        file = serializer.validated_data.get('file', None)
        model = request.data.get('model', 'gpt-4o')
        is_user = True

        logger.debug(
            f"Received data - Content: {content}, Model: {model}, User: {user}, conversation_id: {conversation_id}, file: {file}")

        model_config_map = {
            'gpt-4o': ('o200k_base', 128000, 16000),
            'gpt-4o-mini': ('o200k_base', 128000, 16000),
            'gpt-4.5-preview': ('o200k_base', 128000, 16000),
            'gpt-4o-search-preview': ('o200k_base', 128000, 16000),
            'o3-mini': ('cl100k_base', 200000, 100000),
        }

        encoding_name, context_window, max_output_tokens = model_config_map.get(
            model, ('o200k_base', 120000, 16000))

        max_input_tokens = context_window - max_output_tokens

        # Get or create a conversation for the user
        conversation = None
        if conversation_instance:
            conversation = ChatConversation.objects.filter(
                id=conversation_instance.id, user=user).first()

        elif conversation_id:
            conversation, _ = ChatConversation.objects.get_or_create(
                id=conversation_id,
                user=user,
                defaults={"name": "New Chat"}
            )

        if not conversation:
            try:
                newchat_old = ChatConversation.objects.filter(
                    user=user, name="New Chat").first()
                if newchat_old:
                    newchat_old.delete()
                    logger.debug(
                        f'Removed old "New Chat" for user {user.id} before creating new one.'
                    )

                conversation = ChatConversation.objects.create(
                    user=user, name="New Chat"
                )
                logger.debug(
                    f"Created new conversation with ID: {conversation.id} ({conversation.name}) for user: {user.id}")
            except Exception as e:
                logger.error(
                    f"Failed to create conversation for user {user.username}: {str(e)}"
                )
                raise ValidationError(
                    "Unable to create a new conversation at this time."
                )

        # Gathering messages history
        messages = [{'role': 'user' if msg.is_user else 'assistant',
                    'content': msg.content} for msg in conversation.messages.all()]

        user_message_content = [] if file else content

        if file:
            user_message_content = [{"type": "input_text", "text": content}]
            file_content = file.read()
            file_type, _ = mimetypes.guess_type(file.name)
            file_base64 = base64.b64encode(file_content).decode('utf-8')

            if 'image' in file.content_type:
                print(file.content_type)
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

        # Atualizando o histórico com a mensagem do usuário
        history_entry = {
            "role": "user",
            "content": user_message_content
        }
        messages.append(history_entry)

        history, current_tokens = manage_history_tokens(
            messages, content, encoding_name, max_input_tokens)

        chat_message = ChatMessage.objects.create(
            conversation=conversation,
            content=content,
            file=None,
            # file=file if file else None,
            # file_url= chat_message.file.url,
            is_user=True
        )
        # file_url = chat_message.file.url if chat_message.file else None
        # chat_message.file_url = file_url
        # chat_message.save()

        def event_stream():
            full_ai_message = ""
            try:
                if file:
                    response = client.responses.create(
                        model=model,
                        input=[
                            {
                                "role": "user",
                                "content": user_message_content
                            },
                        ],
                        stream=True
                    )
                    # print(response.output_text, '\n')
                    for event in response:
                        if getattr(event, 'type', None) == 'response.output_text.delta':
                            delta_content = event.delta
                            if delta_content:
                                full_ai_message += delta_content
                                print(delta_content, end='')
                                yield delta_content

                else:
                    response = client.chat.completions.create(
                        model=model,
                        messages=history,
                        stream=True
                    )

                    for chunk in response:
                        content = chunk.choices[0].delta.content
                        if chunk.choices[0].delta.content:
                            full_ai_message += content
                            print(chunk.choices[0].delta.content, end='')
                            yield content

            except Exception as e:
                logger.error("Erro ao fazer streaming: %s", e)
            else:

                ChatMessage.objects.create(
                    conversation=conversation,
                    content=full_ai_message,
                    is_user=False
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
