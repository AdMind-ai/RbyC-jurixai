import json
import os
from pathlib import PurePosixPath
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.http import StreamingHttpResponse
from rest_framework import permissions, serializers, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.services.vera_compliance_service import (
    VeraComplianceConfigurationError,
    VeraComplianceService,
    VeraComplianceServiceError,
    build_vera_session_key,
)


CHAT_UPLOADS_PREFIX = "documents/chat-uploads/"

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


def _session_context_with_chat_session(session_context, session_id):
    context = dict(session_context or {})
    if session_id and not context.get("matter_id"):
        safe_session_id = str(session_id).replace("\\", "-").replace("/", "-").strip()
        context["matter_id"] = f"check-compliance-{safe_session_id}"
    return context


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
