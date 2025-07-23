import os
from rest_framework.views import APIView
from django.http import StreamingHttpResponse
from rest_framework import permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from core.serializers.openai_assistant_message_serializer import OpenAIAssistantMessageSerializer
from core.utils.openai_client import client, logger
from core.utils.delete_file import delete_file
import tempfile


class OpenAISendAssistantMessageView(APIView):
    serializer_class = OpenAIAssistantMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        user = request.user
        serializer = self.serializer_class(data=request.data)
        logger.debug(serializer.is_valid())
        serializer.is_valid(raise_exception=True)

        text = serializer.validated_data.get('text', None)
        file = serializer.validated_data.get('file', None)
        id_assistant = 'asst_Lf1hcV8I3FB4Kp2U5Awdw65c'

        logger.debug(
            f"Received data - Content: {text}, Model: {id_assistant}, User: {user}, file: {file}")

        thread = client.beta.threads.create()       

        if file:
            _, extension = os.path.splitext(file.name)

            temp_file = tempfile.NamedTemporaryFile(
                delete=False, suffix=extension
            )
            temp_file.write(file.read())
            temp_file.close()
            vector_store = client.vector_stores.create(
                name=f'Files to assistant {id_assistant}',
                expires_after= {
                    'anchor': "last_active_at",
                    'days': 360,
                },
            )
            client.vector_stores.file_batches.upload_and_poll(
                vector_store_id=vector_store.id,
                files=[open(temp_file.name, 'rb')],
            )

            client.beta.threads.update(
                thread.id,
                tool_resources={
                    'file_search': {'vector_store_ids': [vector_store.id]}
                },
            )
            text = f"Leggi questo file e crea un post per linkedin. vector_store_id: {vector_store.id}"
            


        messages = [{'type': 'text', 'text': text}]

        def event_stream():
            try:
                client.beta.threads.messages.create(
                thread_id=thread.id,
                role='user',
                content=messages,
                )
                stream = client.beta.threads.runs.create(
                    thread_id=thread.id, assistant_id=id_assistant, stream=True
                )
                for chunk in stream:
                    if (
                        hasattr(chunk, 'event')
                        and chunk.event == 'thread.message.delta'
                        and hasattr(chunk, 'data')
                        and hasattr(chunk.data, 'delta')
                        and hasattr(chunk.data.delta, 'content')
                    ):
                        yield chunk.data.delta.content[0].text.value
                    elif (
                        hasattr(chunk, 'event')
                        and chunk.event == 'thread.run.completed'
                    ):
                        if file:
                            delete_file(temp_file.name)
                        yield ''

            except Exception as e:
                logger.error("Erro ao fazer streaming: %s", e)

        return StreamingHttpResponse(event_stream(), content_type='text/event-stream')
