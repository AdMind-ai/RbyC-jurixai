import json
import logging
import os
import queue
import threading
from pathlib import PurePosixPath
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.http import StreamingHttpResponse
from rest_framework import permissions, serializers, status
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import (
    CheckComplianceAttachment,
    CheckComplianceConversation,
    CheckComplianceMessage,
)
from core.services.vera_compliance_service import (
    VeraComplianceConfigurationError,
    VeraComplianceService,
    VeraComplianceServiceError,
    build_vera_session_key,
)


CHAT_UPLOADS_PREFIX = "documents/chat-uploads/"
logger = logging.getLogger(__name__)

ALLOWED_CHAT_DOCUMENT_EXTENSIONS = {
    ".csv",
    ".doc",
    ".docx",
    ".html",
    ".json",
    ".md",
    ".ods",
    ".odt",
    ".pdf",
    ".ppt",
    ".pptx",
    ".rtf",
    ".txt",
    ".xls",
    ".xlsx",
    ".xml",
}

BLOCKED_CHAT_DOCUMENT_EXTENSIONS = {
    ".bat",
    ".cmd",
    ".com",
    ".dll",
    ".exe",
    ".jar",
    ".js",
    ".msi",
    ".ps1",
    ".scr",
    ".sh",
    ".vbs",
}


class VeraSessionContextSerializer(serializers.Serializer):
    organization_id = serializers.CharField(required=False, allow_blank=True)
    client_id = serializers.CharField(required=False, allow_blank=True)
    matter_id = serializers.CharField(required=False, allow_blank=True)
    user_id = serializers.CharField(required=False, allow_blank=True)


class CheckComplianceChatDocumentReferenceSerializer(serializers.Serializer):
    bucket = serializers.CharField()
    s3_key = serializers.CharField()
    filename = serializers.CharField()
    content_type = serializers.CharField(required=False, allow_blank=True)
    size = serializers.IntegerField(required=False, min_value=0)
    version_id = serializers.CharField(required=False, allow_blank=True)


class CheckComplianceStoredMessageSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["user", "assistant"])
    content = serializers.CharField(required=False, allow_blank=True)
    response_blocks = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        required=False,
        allow_empty=True,
    )
    files = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True,
    )
    documents = serializers.ListField(
        child=CheckComplianceChatDocumentReferenceSerializer(),
        required=False,
        allow_empty=True,
    )


class CheckComplianceConversationSaveSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField(required=False)
    title = serializers.CharField(max_length=255)
    vera_session_id = serializers.CharField(max_length=128)
    messages = serializers.ListField(
        child=CheckComplianceStoredMessageSerializer(),
        required=True,
        allow_empty=True,
    )


class CheckComplianceChatInputSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, allow_blank=False)
    session_id = serializers.CharField(required=False, allow_blank=True)
    stream = serializers.BooleanField(required=False, default=False)
    session_context = VeraSessionContextSerializer(required=False)
    documents = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True,
    )


def _encode_sse_event(event_name, payload):
    return f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
        aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
        region_name=getattr(settings, "AWS_S3_REGION_NAME", None),
    )


def _chat_bucket_name():
    return getattr(settings, "COMPLIANCE_CHAT_BUCKET_NAME", None)


def _chat_upload_prefix():
    prefix = (
        getattr(settings, "COMPLIANCE_CHAT_UPLOAD_PREFIX", None)
        or CHAT_UPLOADS_PREFIX
    )
    prefix = prefix.replace("\\", "/").strip().lstrip("/")
    if prefix and not prefix.endswith("/"):
        prefix += "/"
    return prefix


def _safe_filename(filename):
    name = os.path.basename((filename or "").replace("\\", "/")).strip()
    if not name or name in {".", ".."}:
        raise ValueError("Invalid file name.")
    if any(char in name for char in ("\x00", "/", "\\")):
        raise ValueError("File name contains invalid characters.")
    return name


def _validate_chat_file(file_obj):
    filename = _safe_filename(file_obj.name)
    extension = PurePosixPath(filename).suffix.lower()
    if extension in BLOCKED_CHAT_DOCUMENT_EXTENSIONS:
        raise ValueError("This file type is not allowed.")
    if not extension:
        raise ValueError("Files must include an extension.")
    if extension not in ALLOWED_CHAT_DOCUMENT_EXTENSIONS:
        raise ValueError("This file extension is not supported.")

    max_size = getattr(settings, "COMPLIANCE_CHAT_MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    if file_obj.size and file_obj.size > max_size:
        raise ValueError("File exceeds the maximum allowed size.")

    return filename


def _build_upload_key(user, session_id, filename):
    prefix = _chat_upload_prefix()
    user_id = getattr(user, "pk", None) or "anonymous"
    session_part = (session_id or str(uuid4())).strip() or str(uuid4())
    session_part = session_part.replace("\\", "-").replace("/", "-")
    return f"{prefix}{user_id}/{session_part}/{uuid4().hex}-{filename}"


def _build_vera_content(message, documents):
    if not documents:
        return message

    payload = {
        "question": message,
        "documents": documents,
        "instructions": (
            "Use the S3 document references as the source documents for this "
            "compliance analysis. The references are textual metadata only; "
            "read the files from S3 using the granted IAM permissions."
        ),
    }
    return json.dumps(payload, ensure_ascii=False)


def _conversation_summary(conversation):
    return {
        "id": str(conversation.id),
        "title": conversation.title,
        "vera_session_id": conversation.vera_session_id,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
    }


def _message_payload(message):
    provider_payload = message.provider_payload or {}
    return {
        "id": str(message.id),
        "role": message.role,
        "content": message.content,
        "response_blocks": provider_payload.get("response_blocks") or [],
        "files": provider_payload.get("files") or [],
        "documents": provider_payload.get("documents") or [],
        "created_at": message.created_at,
    }


def _replace_conversation_messages(conversation, messages):
    conversation.messages.all().delete()
    for item in messages:
        files = item.get("files") or []
        documents = item.get("documents") or []
        response_blocks = item.get("response_blocks") or []
        message = CheckComplianceMessage.objects.create(
            conversation=conversation,
            role=item["role"],
            content=item.get("content", ""),
            provider_payload={
                "response_blocks": response_blocks,
                "files": files,
                "documents": documents,
            },
        )
        CheckComplianceAttachment.objects.bulk_create(
            [
                CheckComplianceAttachment(
                    conversation=conversation,
                    message=message,
                    bucket=document["bucket"],
                    s3_key=document["s3_key"],
                    filename=document["filename"],
                    content_type=document.get("content_type", ""),
                    size=document.get("size") or 0,
                    version_id=document.get("version_id") or None,
                )
                for document in documents
            ]
        )


def _session_context_with_chat_session(session_context, session_id):
    context = dict(session_context or {})
    if session_id and not context.get("matter_id"):
        safe_session_id = str(session_id).replace("\\", "-").replace("/", "-").strip()
        context["matter_id"] = f"check-compliance-{safe_session_id}"
    return context


class CheckComplianceConversationListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        conversations = CheckComplianceConversation.objects.filter(
            user=request.user,
            is_saved=True,
        ).order_by("-updated_at")
        return Response([_conversation_summary(conversation) for conversation in conversations])

    def post(self, request):
        serializer = CheckComplianceConversationSaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        conversation_id = data.get("conversation_id")
        if conversation_id:
            conversation = get_object_or_404(
                CheckComplianceConversation,
                id=conversation_id,
                user=request.user,
            )
            created = False
        else:
            conversation = CheckComplianceConversation(
                user=request.user,
                vera_session_id=data["vera_session_id"],
            )
            created = True

        conversation.title = data["title"]
        conversation.vera_session_id = data["vera_session_id"]
        conversation.is_saved = True
        conversation.save()
        _replace_conversation_messages(conversation, data["messages"])

        return Response(
            _conversation_summary(conversation),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class CheckComplianceConversationDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, conversation_id):
        conversation = get_object_or_404(
            CheckComplianceConversation,
            id=conversation_id,
            user=request.user,
            is_saved=True,
        )
        return Response(
            {
                **_conversation_summary(conversation),
                "messages": [
                    _message_payload(message)
                    for message in conversation.messages.order_by("created_at")
                ],
            }
        )

    def delete(self, request, conversation_id):
        conversation = get_object_or_404(
            CheckComplianceConversation,
            id=conversation_id,
            user=request.user,
        )
        conversation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CheckComplianceChatView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request):
        serializer = CheckComplianceChatInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = serializer.validated_data["message"].strip()
        stream = serializer.validated_data.get("stream", False)
        session_context = serializer.validated_data.get("session_context") or {}
        session_id = serializer.validated_data.get("session_id")
        documents = serializer.validated_data.get("documents") or []
        session_key = build_vera_session_key(
            request.user,
            _session_context_with_chat_session(session_context, session_id),
        )
        vera_content = _build_vera_content(message, documents)

        if stream:
            return self._stream_response(vera_content, session_key)

        try:
            service = VeraComplianceService()
            answer = service.send_message(
                messages=[
                    {
                        "role": "user",
                        "content": vera_content,
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
            stream_queue = queue.Queue()
            keepalive_seconds = getattr(settings, "VERA_API_STREAM_KEEPALIVE_SECONDS", 15)

            def run_vera_stream():
                try:
                    service = VeraComplianceService()
                    for delta in service.stream_message(
                        messages=[
                            {
                                "role": "user",
                                "content": message,
                            }
                        ],
                        session_key=session_key,
                    ):
                        stream_queue.put(("delta", delta))
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
                                "message": "Vera sta ancora analizzando la richiesta.",
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

                    if event_type == "done":
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
                logger.exception("Unexpected error during Vera compliance streaming.")
                yield _encode_sse_event(
                    "error",
                    {
                        "type": "error",
                        "message": "Unexpected error during Vera compliance streaming.",
                    },
                )

        response = StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class CheckComplianceChatAttachmentUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        bucket = _chat_bucket_name()
        if not bucket:
            return Response(
                {"detail": "Compliance chat bucket is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        files = request.FILES.getlist("file")
        if not files:
            return Response(
                {"detail": 'No file provided. Use field "file".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session_id = request.data.get("session_id") or str(uuid4())
        upload_items = []
        try:
            for file_obj in files:
                filename = _validate_chat_file(file_obj)
                key = _build_upload_key(request.user, session_id, filename)
                upload_items.append((file_obj, filename, key))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        s3 = _s3_client()
        documents = []
        for file_obj, filename, key in upload_items:
            content_type = file_obj.content_type or "application/octet-stream"
            try:
                response = s3.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=file_obj,
                    ContentType=content_type,
                    Metadata={
                        "uploaded-by": str(request.user.pk),
                        "original-filename": filename,
                        "source": "check-compliance-chat",
                    },
                )
            except ClientError as exc:
                return Response(
                    {
                        "detail": "Error uploading compliance chat attachment.",
                        "error": str(exc),
                    },
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            document = {
                "bucket": bucket,
                "s3_key": key,
                "filename": filename,
                "content_type": content_type,
                "size": file_obj.size,
            }
            version_id = response.get("VersionId")
            if version_id:
                document["version_id"] = version_id

            documents.append(document)

        return Response(
            {
                "sessionId": session_id,
                "documents": documents,
            },
            status=status.HTTP_201_CREATED,
        )
