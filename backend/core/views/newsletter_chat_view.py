import logging
import json
import queue
import threading
import base64
import binascii
from uuid import uuid4

from django.conf import settings
from django.http import StreamingHttpResponse
from rest_framework import permissions, serializers, status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models.usage import UsageTool
from core.services.usage_tracking import UsageTrackingService
from core.utils.storage import upload_bytes_to_s3_bucket
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

NEWSLETTER_UPLOADS_PREFIX = "documents/newsletter-uploads/"


class NewsletterAttachmentSerializer(serializers.Serializer):
    name = serializers.CharField(required=True, allow_blank=False)
    size = serializers.IntegerField(required=False, min_value=0, default=0)
    type = serializers.CharField(required=False, allow_blank=True, default="")
    data = serializers.CharField(required=True, allow_blank=False)


class NewsletterChatInputSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, allow_blank=True)
    session_id = serializers.CharField(required=False, allow_blank=True, default="")
    stream = serializers.BooleanField(required=False, default=False)
    draft_type = serializers.ChoiceField(
        choices=["newsletter", "pill"],
        required=False,
        default="newsletter",
    )
    attachments = NewsletterAttachmentSerializer(many=True, required=False, default=list)

    def validate(self, attrs):
        message = (attrs.get("message") or "").strip()
        attachments = attrs.get("attachments") or []
        if not message and not attachments:
            raise serializers.ValidationError("Message or attachments are required.")
        return attrs


def _encode_sse_event(event_name, payload):
    return f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _newsletter_bucket_name():
    return (
        getattr(settings, "NEWSLETTER_CHAT_BUCKET_NAME", None)
        or getattr(settings, "COMPLIANCE_CHAT_BUCKET_NAME", None)
    )


def _newsletter_upload_prefix():
    prefix = (
        getattr(settings, "NEWSLETTER_CHAT_UPLOAD_PREFIX", None)
        or getattr(settings, "COMPLIANCE_CHAT_UPLOAD_PREFIX", None)
        or NEWSLETTER_UPLOADS_PREFIX
    )
    prefix = prefix.replace("\\", "/").strip().lstrip("/")
    if prefix and not prefix.endswith("/"):
        prefix += "/"
    return prefix


def _safe_filename(filename):
    name = (filename or "").replace("\\", "/").split("/")[-1].strip()
    if not name or name in {".", ".."} or "\x00" in name:
        raise ValueError("Invalid file name.")
    return name


def _build_upload_key(user, session_id, filename):
    prefix = _newsletter_upload_prefix()
    user_id = getattr(user, "pk", None) or "anonymous"
    session_part = (session_id or str(uuid4())).strip() or str(uuid4())
    session_part = session_part.replace("\\", "-").replace("/", "-")
    return f"{prefix}{user_id}/{session_part}/{uuid4().hex}-{filename}"


def _decode_attachment_data(data):
    raw = data or ""
    if "," in raw and raw.lower().startswith("data:"):
        raw = raw.split(",", 1)[1]
    return base64.b64decode(raw, validate=True)


def _store_attachments(user, session_id, attachments):
    if not attachments:
        return []

    bucket = _newsletter_bucket_name()
    if not bucket:
        raise VeraComplianceConfigurationError("Newsletter attachments bucket is not configured.")

    documents = []
    for attachment in attachments:
        filename = _safe_filename(attachment.get("name"))
        content_type = attachment.get("type") or "application/octet-stream"
        file_bytes = _decode_attachment_data(attachment.get("data"))
        object_key = _build_upload_key(user, session_id, filename)
        upload_bytes_to_s3_bucket(
            file_bytes,
            object_key,
            bucket,
            content_type=content_type,
        )
        documents.append(
            {
                "bucket": bucket,
                "s3_key": object_key,
                "filename": filename,
                "content_type": content_type,
                "size": len(file_bytes),
            }
        )
    return documents


def _enrich_prompt(message: str, draft_type: str, tag: str, documents=None) -> str:
    """
    Adds channel-specific instructions before sending the user message to Vera.
    """
    type_label = DRAFT_TYPE_LABEL.get(draft_type, "Newsletter normativa")
    document_block = ""
    if documents:
        document_block = (
            "\n\nDOCUMENTI ALLEGATI DALL'UTENTE:\n"
            "I documenti seguenti sono stati allegati alla richiesta. "
            "Le referenze sono metadati testuali: leggi i file da S3 usando i permessi IAM disponibili.\n"
            f"{json.dumps(documents, ensure_ascii=False)}"
        )

    user_message = message or "Analizza i documenti allegati e genera la bozza richiesta."

    return (
        f"{tag} [Richiesta: {type_label}]\n"
        "ISTRUZIONE DI FORMATO: quando generi la bozza definitiva del documento, "
        "inseriscila SEMPRE all'interno di un unico blocco <bozza> e </bozza>. "
        "Tutto cio che e conversazionale (domande, chiarimenti, intro, conclusioni) "
        "va FUORI dai tag. "
        "Il blocco <bozza>...</bozza> deve essere l'ultimo elemento isolato della risposta, "
        "senza testo dopo la chiusura di </bozza>. "
        'Esempio: "Ecco la bozza:\\n\\n<bozza>...testo...</bozza>"\n\n'
        f"{user_message}"
        f"{document_block}"
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
        attachments = serializer.validated_data.get("attachments") or []

        vera_tag = DRAFT_TYPE_TAG.get(draft_type, "[NEWSLETTER]")

        session_context = {}
        if session_id:
            safe_session_id = session_id.replace("\\", "-").replace("/", "-").strip()
            session_context["matter_id"] = f"newsletter-{safe_session_id}"

        session_key = build_vera_session_key(request.user, session_context)
        try:
            documents = _store_attachments(request.user, session_key, attachments)
        except (ValueError, binascii.Error, VeraComplianceConfigurationError):
            logger.exception("Erro ao preparar anexos Newsletter/PILL para Vera.")
            return Response(
                {"detail": "Error preparing newsletter attachments."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        enriched_message = _enrich_prompt(raw_message, draft_type, vera_tag, documents)

        if stream:
            return self._stream_response(
                enriched_message,
                session_key,
                request=request,
                raw_message=raw_message,
                draft_type=draft_type,
                attachments=attachments,
                documents=documents,
            )

        try:
            service = VeraComplianceService()
            answer = service.send_message(
                messages=[{"role": "user", "content": enriched_message}],
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

        self._record_newsletter_usage(
            request=request,
            session_key=session_key,
            raw_message=raw_message,
            draft_type=draft_type,
            streamed=False,
            attachments=attachments,
        )

        return Response(
            {"answer": answer, "sessionKey": session_key, "documents": documents},
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _record_newsletter_usage(
        *,
        request,
        session_key,
        raw_message,
        draft_type,
        streamed,
        attachments=None,
    ):
        UsageTrackingService.record_usage_event(
            user=request.user,
            tool=UsageTool.NEWSLETTER_PILL,
            quantity=1,
            company=getattr(request.user, "company", None),
            metadata={
                "source": "newsletter_chat",
                "draft_type": draft_type,
                "session_key": session_key,
                "message_length": len(raw_message or ""),
                "attachment_count": len(attachments or []),
                "streamed": streamed,
            },
        )

    def _stream_response(
        self,
        message,
        session_key,
        tag=None,
        request=None,
        raw_message="",
        draft_type="newsletter",
        attachments=None,
        documents=None,
    ):
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
                                "documents": documents or [],
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
                        if request is not None:
                            self._record_newsletter_usage(
                                request=request,
                                session_key=session_key,
                                raw_message=raw_message,
                                draft_type=draft_type,
                                streamed=True,
                                attachments=attachments or [],
                            )
                        yield _encode_sse_event(
                            "answer_completed",
                            {
                                "type": "answer_completed",
                                "answer": full_answer,
                                "session_key": session_key,
                                "documents": documents or [],
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
