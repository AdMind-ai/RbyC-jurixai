import logging
import json
import queue
import threading

from django.conf import settings
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

logger = logging.getLogger(__name__)

DRAFT_TYPE_LABEL = {
    "newsletter": "Newsletter normativa",
    "pill": "PILL formativo",
}

DRAFT_TYPE_TAG = {
    "newsletter": "[NEWSLETTER]",
    "pill": "[PILL FORMATIVO]",
}


class NewsletterChatInputSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, allow_blank=False)
    session_id = serializers.CharField(required=False, allow_blank=True, default="")
    stream = serializers.BooleanField(required=False, default=False)
    draft_type = serializers.ChoiceField(
        choices=["newsletter", "pill"],
        required=False,
        default="newsletter",
    )


def _encode_sse_event(event_name, payload):
    return f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _enrich_prompt(message: str, draft_type: str) -> str:
    """
    Adds channel-specific instructions before sending the user message to Vera.
    """
    type_label = DRAFT_TYPE_LABEL.get(draft_type, "Newsletter normativa")
    return (
        f"[Richiesta: {type_label}]\n"
        "ISTRUZIONE DI FORMATO: quando generi la bozza definitiva del documento, "
        "inseriscila SEMPRE all'interno di un unico blocco <bozza> e </bozza>. "
        "Tutto cio che e conversazionale (domande, chiarimenti, intro, conclusioni) "
        "va FUORI dai tag. "
        "Il blocco <bozza>...</bozza> deve essere l'ultimo elemento isolato della risposta, "
        "senza testo dopo la chiusura di </bozza>. "
        'Esempio: "Ecco la bozza:\\n\\n<bozza>...testo...</bozza>"\n\n'
        f"{message}"
    )


class NewsletterChatView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request):
        serializer = NewsletterChatInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        raw_message = serializer.validated_data["message"].strip()
        session_id = serializer.validated_data.get("session_id") or ""
        stream = serializer.validated_data.get("stream", False)
        draft_type = serializer.validated_data.get("draft_type", "newsletter")

        vera_tag = DRAFT_TYPE_TAG.get(draft_type, "[NEWSLETTER]")
        enriched_message = _enrich_prompt(raw_message, draft_type)

        session_context = {}
        if session_id:
            safe_session_id = session_id.replace("\\", "-").replace("/", "-").strip()
            session_context["matter_id"] = f"newsletter-{safe_session_id}"

        session_key = build_vera_session_key(request.user, session_context)

        if stream:
            return self._stream_response(enriched_message, session_key, tag=vera_tag)

        try:
            service = VeraComplianceService()
            answer = service.send_message(
                messages=[{"role": "user", "content": enriched_message}],
                session_key=session_key,
                tag=vera_tag,
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
            {"answer": answer, "sessionKey": session_key},
            status=status.HTTP_200_OK,
        )

    def _stream_response(self, message, session_key, tag=None):
        def event_stream():
            full_answer = ""
            stream_queue = queue.Queue()
            keepalive_seconds = getattr(settings, "VERA_API_STREAM_KEEPALIVE_SECONDS", 15)

            def run_vera_stream():
                try:
                    service = VeraComplianceService()
                    for event in service.stream_message_events(
                        messages=[{"role": "user", "content": message}],
                        session_key=session_key,
                        tag=tag,
                    ):
                        event_type = event.get("type")
                        if event_type == "answer_delta":
                            stream_queue.put(("delta", event.get("delta") or ""))
                        elif event_type == "run_status":
                            stream_queue.put(("run_status", event.get("message") or ""))
                        elif event_type == "answer_completed":
                            stream_queue.put(("done", event.get("answer") or ""))
                            return
                    stream_queue.put(("done", None))
                except VeraComplianceConfigurationError:
                    stream_queue.put(("configuration_error", None))
                except VeraComplianceServiceError:
                    stream_queue.put(("service_error", None))

            worker = threading.Thread(target=run_vera_stream, daemon=True)
            worker.start()

            try:
                yield _encode_sse_event(
                    "answer_started",
                    {
                        "type": "answer_started",
                        "session_key": session_key,
                    },
                )

                while True:
                    try:
                        event_type, payload = stream_queue.get(timeout=keepalive_seconds)
                    except queue.Empty:
                        yield _encode_sse_event(
                            "answer_keepalive",
                            {
                                "type": "answer_keepalive",
                                "message": "Vera sta ancora elaborando la richiesta.",
                                "session_key": session_key,
                            },
                        )
                        continue

                    if event_type == "delta":
                        full_answer += payload
                        yield _encode_sse_event(
                            "answer_delta",
                            {
                                "type": "answer_delta",
                                "delta": payload,
                                "session_key": session_key,
                            },
                        )
                        continue

                    if event_type == "run_status":
                        yield _encode_sse_event(
                            "run_status",
                            {
                                "type": "run_status",
                                "message": payload,
                                "session_key": session_key,
                            },
                        )
                        continue

                    if event_type == "done":
                        if payload:
                            full_answer = payload
                        yield _encode_sse_event(
                            "answer_completed",
                            {
                                "type": "answer_completed",
                                "answer": full_answer,
                                "session_key": session_key,
                            },
                        )
                        return

                    if event_type == "configuration_error":
                        yield _encode_sse_event(
                            "error",
                            {
                                "type": "error",
                                "message": "Vera API is not configured.",
                            },
                        )
                        return

                    if event_type == "service_error":
                        yield _encode_sse_event(
                            "error",
                            {
                                "type": "error",
                                "message": "Error calling Vera compliance service.",
                            },
                        )
                        return
            except Exception:
                logger.exception("Unexpected error during Vera newsletter streaming.")
                yield _encode_sse_event(
                    "error",
                    {
                        "type": "error",
                        "message": "Unexpected error during Vera newsletter streaming.",
                    },
                )

        response = StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
