import json

from django.http import StreamingHttpResponse
from rest_framework import permissions, serializers, status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.services.vera_compliance_service import (
    VeraComplianceConfigurationError,
    VeraComplianceService,
    VeraComplianceServiceError,
    build_vera_session_key,
)


class VeraSessionContextSerializer(serializers.Serializer):
    organization_id = serializers.CharField(required=False, allow_blank=True)
    client_id = serializers.CharField(required=False, allow_blank=True)
    matter_id = serializers.CharField(required=False, allow_blank=True)
    user_id = serializers.CharField(required=False, allow_blank=True)


class CheckComplianceChatInputSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, allow_blank=False)
    session_id = serializers.CharField(required=False, allow_blank=True)
    stream = serializers.BooleanField(required=False, default=False)
    session_context = VeraSessionContextSerializer(required=False)


def _encode_sse_event(event_name, payload):
    return f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


class CheckComplianceChatView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request):
        serializer = CheckComplianceChatInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = serializer.validated_data["message"].strip()
        stream = serializer.validated_data.get("stream", False)
        session_context = serializer.validated_data.get("session_context") or {}
        session_key = build_vera_session_key(request.user, session_context)

        if stream:
            return self._stream_response(message, session_key)

        try:
            service = VeraComplianceService()
            answer = service.send_message(
                messages=[
                    {
                        "role": "user",
                        "content": message,
                    }
                ],
                session_key=session_key,
            )
        except VeraComplianceConfigurationError:
            return Response(
                {"detail": "Vera API is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except VeraComplianceServiceError:
            return Response(
                {"detail": "Error calling Vera compliance service."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "answer": answer,
                "sessionKey": session_key,
            },
            status=status.HTTP_200_OK,
        )

    def _stream_response(self, message, session_key):
        def event_stream():
            full_answer = ""
            try:
                service = VeraComplianceService()
                yield _encode_sse_event(
                    "answer_started",
                    {
                        "type": "answer_started",
                        "session_key": session_key,
                    },
                )

                for delta in service.stream_message(
                    messages=[
                        {
                            "role": "user",
                            "content": message,
                        }
                    ],
                    session_key=session_key,
                ):
                    full_answer += delta
                    yield _encode_sse_event(
                        "answer_delta",
                        {
                            "type": "answer_delta",
                            "delta": delta,
                            "session_key": session_key,
                        },
                    )

                yield _encode_sse_event(
                    "answer_completed",
                    {
                        "type": "answer_completed",
                        "answer": full_answer,
                        "session_key": session_key,
                    },
                )
            except VeraComplianceConfigurationError:
                yield _encode_sse_event(
                    "error",
                    {
                        "type": "error",
                        "message": "Vera API is not configured.",
                    },
                )
            except VeraComplianceServiceError:
                yield _encode_sse_event(
                    "error",
                    {
                        "type": "error",
                        "message": "Error calling Vera compliance service.",
                    },
                )

        response = StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
