# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.http import StreamingHttpResponse
from core.utils.openai_client import client, logger
from core.utils.encode_file import encode_file_base64
from django.conf import settings

class CheckComplianceView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        conversation_id = request.data.get("conversation_id")
        file = request.FILES.get("file")
        input_text = request.data.get("input_text")  # Mensagem do usuário

        if not file and not conversation_id and not input_text:
            return Response(
                {"error": "File or conversation_id/input_text is required."},
                status=400
            )

        base64_string = encode_file_base64(file) if file else None

        def event_stream():
            full_ai_message = ""
            try:
                # Monta entrada para API
                inputs = []
                if base64_string:
                    inputs.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "input_file",
                                "filename": file.name,
                                "file_data": f"data:application/pdf;base64,{base64_string}"
                            }
                        ]
                    })
                if input_text:
                    inputs.append({
                        "role": "user",
                        "content": [{"type": "input_text", "text": input_text}]
                    })

                response = client.responses.create(
                    prompt={"id": settings.OPENAI_PROMPT_ID_CHECK_COMPLIANCE_RBYC },
                    input=inputs,
                    conversation=conversation_id,
                    store=True,
                    stream=True,
                    timeout=600,
                )

                for event in response:
                    if getattr(event, "type", None) == "response.output_text.delta":
                        delta_content = event.delta
                        if delta_content:
                            full_ai_message += delta_content
                            yield delta_content

            except Exception as e:
                logger.error("Erro no streaming: %s", e)
                yield f"Erro: {str(e)}"

        return StreamingHttpResponse(
            event_stream(),
            content_type="text/plain",
            headers={"Cache-Control": "no-cache"}
        )
