# views.py
from django.conf import settings
from django.http import StreamingHttpResponse
from rest_framework import permissions, status, serializers
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import JSONParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from core.utils.openai_client import client, logger
from core.utils.common import safe_load_json
from core.utils.encode_file import encode_file_base64


class ComplianceFileSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True)
    mimeType = serializers.CharField(required=False, allow_blank=True)
    data = serializers.CharField(required=True, allow_blank=False)


class CheckComplianceAnalyzeInputSerializer(serializers.Serializer):
    files = ComplianceFileSerializer(many=True)
    norms = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
        allow_empty=False,
    )


class CheckComplianceAnalyzeView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request):
        serializer = CheckComplianceAnalyzeInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        files = serializer.validated_data["files"]
        norms = serializer.validated_data["norms"]
        prompt_id = settings.OPENAI_PROMPT_ID_CHECK_COMPLIANCE_RBYC

        if not files:
            raise ValidationError("At least one PDF file is required.")

        if not prompt_id:
            raise ValidationError("OpenAI check compliance prompt id is not configured.")

        user_content = [
            {
                "type": "input_text",
                "text": (
                    "Normative selezionate dall'utente:\n"
                    + "\n".join(f"- {norm}" for norm in norms)
                ),
            }
        ]

        for index, file_payload in enumerate(files, start=1):
            mime_type = file_payload.get("mimeType") or "application/pdf"
            if "pdf" not in mime_type.lower():
                raise ValidationError("Only PDF files are allowed for compliance analysis.")

            file_data = file_payload["data"]
            if not file_data.startswith("data:"):
                file_data = f"data:{mime_type};base64,{file_data}"

            user_content.append(
                {
                    "type": "input_file",
                    "filename": file_payload.get("name") or f"document-{index}.pdf",
                    "file_data": file_data,
                }
            )

        tools = self._build_tools(norms)

        request_kwargs = {
            "prompt": {"id": prompt_id},
            "input": [
                {
                    "role": "user",
                    "content": user_content,
                }
            ],
            "store": True,
            "timeout": 900,
        }
        if tools:
            request_kwargs["tools"] = tools

        try:
            response = client.responses.create(**request_kwargs)
            raw_output = getattr(response, "output_text", "") or ""
            parsed_output = safe_load_json(raw_output)
        except Exception as exc:
            logger.exception("Error calling OpenAI check compliance analysis: %s", exc)
            return Response(
                {"detail": "Error analyzing compliance document."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if parsed_output == [] and raw_output.strip() not in ("[]", "```[]```"):
            logger.error(
                "Unable to parse check compliance response from OpenAI: %s",
                raw_output[:1000],
            )
            return Response(
                {"detail": "Invalid compliance analysis format."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if isinstance(parsed_output, list):
            parsed_output = {"segments": parsed_output}

        if not isinstance(parsed_output, dict) or not isinstance(
            parsed_output.get("segments"), list
        ):
            logger.error(
                "Invalid check compliance response format from OpenAI: %s",
                raw_output[:1000],
            )
            return Response(
                {"detail": "Invalid compliance analysis format."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(parsed_output, status=status.HTTP_200_OK)

    @staticmethod
    def _build_tools(norms):
        if "Database customizzato" not in norms:
            return []

        server_url = getattr(settings, "CHECK_COMPLIANCE_MCP_SERVER_URL", None)
        if not server_url:
            raise ValidationError(
                "Check compliance MCP server URL is required for Database customizzato."
            )

        tool = {
            "type": "mcp",
            "server_label": "check-compliance-jurix",
            "server_url": server_url,
            "require_approval": "never",
        }

        return [tool]


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
