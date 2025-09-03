from django.conf import settings
import warnings
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.http import StreamingHttpResponse
from rest_framework.response import Response
from openai import AssistantEventHandler, OpenAI
from typing_extensions import override
from rest_framework import serializers

# Functions
from core.utils.assistants import *
from core.views.openai.chat.assistant.tool_call_dispatcher import dispatch_tool_call

from core.models.openai_chat_models import ChatConversation, ChatMessage
from core.models.assistant_thread_model import AssistantThread
from django.db import transaction

# Suprimindo warnings irrelevantes
warnings.filterwarnings("ignore", category=DeprecationWarning)

client = OpenAI(api_key=settings.OPENAI_KEY)


def cancel_active_run_if_exists(thread_id):
    runs = client.beta.threads.runs.list(thread_id=thread_id)
    for run in runs.data:
        if run.status in ("in_progress", "queued", "requires_action"):
            print(f"Cancelling ACTIVE run: {run.id}")
            client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run.id)
            break


class AssistantMessageSerializer(serializers.Serializer):
    thread_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    content = serializers.CharField(required=True, allow_blank=False)


class DjangoStreamingEventHandler(AssistantEventHandler):
    """
    Herda a lógica do seu handler, mas armazena a saída em buffers e gera via yield
    """

    def __init__(self):
        super().__init__()
        self._buffer = []
        self._citations = []

    @override
    def on_text_created(self, text) -> None:
        # if text:
        #     self._buffer.append(text)
        pass

    @override
    def on_text_delta(self, delta, snapshot):
        if delta.value:
            self._buffer.append(delta.value)

    @override
    def on_tool_call_created(self, tool_call):
        txt = f"\n[assistant tool_call: {tool_call.type}]"
        try:
            txt += f" - {tool_call.function.name}\n"
        except Exception:
            txt += "\n"
        print(txt, flush=True)
        # self._buffer.append(txt)

    @override
    def on_message_done(self, message) -> None:
        message_content = message.content[0].text

        msg_val = message_content.value.strip()
        # self._buffer.append("\n" + message_content.value + "\n")
        # Só adicione ao buffer se não está lá (evita duplicata caso stream funcione normalmente)

        print("BUFFER>>>", self._buffer, "<<<")
        print(msg_val, flush=True)
        # annotations = message_content.annotations
        # for index, annotation in enumerate(annotations):
        #     # Substitui texto citado por [index]
        #     message_content.value = message_content.value.replace(
        #         annotation.text, f"[{index}]"
        #     )
        #     if file_citation := getattr(annotation, "file_citation", None):
        #         cited_file = client.files.retrieve(file_citation.file_id)
        #         self._citations.append(f"[{index}] {cited_file.filename}")

        # # Ao final, adiciona texto e citações (se houver)
        # self._buffer.append("\n" + message_content.value + "\n")
        # if self._citations:
        #     self._buffer.append("\n".join(self._citations) + "\n")

    @override
    def on_event(self, event):
        # Se for necessário executar uma função tool_call
        if event.event == 'thread.run.requires_action':
            run_id = event.data.id
            self.handle_requires_action(event.data, run_id)

    def handle_requires_action(self, data, run_id):
        tool_outputs = []

        for tool in data.required_action.submit_tool_outputs.tool_calls:
            dispatch_tool_call(tool, tool_outputs)

        self.submit_tool_outputs(tool_outputs, run_id)

    def submit_tool_outputs(self, tool_outputs, run_id):
        # Stream dos outputs das tools (pode ser englobado no buffer também se necessário)
        with client.beta.threads.runs.submit_tool_outputs_stream(
            thread_id=self.current_run.thread_id,
            run_id=self.current_run.id,
            tool_outputs=tool_outputs,
            event_handler=DjangoStreamingEventHandler(),
        ) as stream:
            for text in stream.text_deltas:
                self._buffer.append(text)

    def pop_buffer(self):
        # Método auxiliar para retirar tudo da fila e enviar pro stream do Django
        while self._buffer:
            yield self._buffer.pop(0)


class AssistantStreamingView(APIView):
    """
    View que transmite a resposta do assistente por streaming,
    com suporte a tool calls, file search, etc.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AssistantMessageSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        prompt = serializer.validated_data["content"]
        thread_id = serializer.validated_data["thread_id"]

        with transaction.atomic():
            assistant_thread = None

            if thread_id:
                assistant_thread = AssistantThread.objects.filter(thread_id=thread_id).first()
                if not assistant_thread:
                    # thread_id inválido → criar novo registro
                    conversation_openai = client.conversations.create()
                    print(conversation_openai)
                    assistant_thread = AssistantThread.objects.create(thread_id=conversation_openai.id, active=True)
            else:
                # cria thread local, id será preenchido depois
                conversation_openai = client.conversations.create()
                print(conversation_openai)
                assistant_thread = AssistantThread.objects.create(thread_id=conversation_openai.id, active=True)

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

        # salva a mensagem do usuário
        ChatMessage.objects.create(
            conversation=conversation,
            content=prompt,
            is_user=True
        )

        # cancel_active_run_if_exists(thread_id)

        def openai_stream():
            full_ai_message = ""

            with client.responses.create(
                model="gpt-5",
                prompt = { "id": settings.OPENAI_PROMPT_ID_RBYC },
                input=[
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": prompt}]
                    }
                ],
                conversation=assistant_thread.thread_id,
                tools=[
                    {
                        "type": "file_search",
                        "vector_store_ids": [settings.VECTOR_STORE_ID_RBYC]
                    }
                ],
                store=True,
                stream=True,
                include=["reasoning.encrypted_content", "web_search_call.action.sources"],
                timeout=600,
            ) as stream:
                handler = DjangoStreamingEventHandler()
                print("Stream started", flush=True)
                for event in stream:
                    if event.type == "response.output_text.delta":
                        chunk = event.delta
                        full_ai_message += chunk
                        yield chunk
                    # elif event.type == "response.completed":
                    #     new_conversation_id = event.response.conversation
                # stream.until_done()
                print("Stream ended", flush=True)

            # salva a resposta da IA
            ChatMessage.objects.create(
                conversation=conversation,
                content=full_ai_message,
                is_user=False
            )

        return StreamingHttpResponse(openai_stream(), content_type="text/plain")


class AssistantLawConsultantView(APIView):
    """
    Endpoint para consultas jurídicas com o assistente.
    """
    serializer_class = AssistantMessageSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        prompt = serializer.validated_data["content"]
        thread_id = serializer.validated_data["thread_id"]

        if not thread_id:
            return Response({"error": "thread_id is required"}, status=400)

        cancel_active_run_if_exists(thread_id)
        
        def openai_stream():
            _ = client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=prompt,
            )
            handler = DjangoStreamingEventHandler()
            # São yields que serão enviados p/ StreamingHttpResponse
            
            with client.beta.threads.runs.stream(
                thread_id=thread_id,
                assistant_id=settings.OPENAI_ASSISTANT_ID_RBYC_LAW_CONSULTANT,
                event_handler=handler,
            ) as stream:
                print("Stream started", flush=True)
                for _ in stream:
                    for chunk in handler.pop_buffer():
                        print(chunk, end="", flush=True)
                        yield chunk
                for chunk in handler.pop_buffer():
                    yield chunk
                stream.until_done()
                print("Stream ended", flush=True)
                
        print("Starting streaming response for law consultant", flush=True)

        return StreamingHttpResponse(openai_stream(), content_type="text/plain")