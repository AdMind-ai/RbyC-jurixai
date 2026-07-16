import os
from pathlib import PurePosixPath

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


DOCUMENTS_PREFIX = "documents/"

ALLOWED_EXTENSIONS = {
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

BLOCKED_EXTENSIONS = {
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


def _s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
        aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
        region_name=getattr(settings, "COMPLIANCE_DOCUMENTS_BUCKET_REGION", None),
    )


def _bucket_name():
    return (
        getattr(settings, "COMPLIANCE_DOCUMENTS_BUCKET_NAME", None)
        or getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
    )


def _normalize_prefix(prefix):
    value = (prefix or DOCUMENTS_PREFIX).replace("\\", "/").strip()
    value = value.lstrip("/")
    if value and not value.endswith("/"):
        value += "/"
    return value


def _validate_key(key, allowed_prefixes):
    value = (key or "").replace("\\", "/").strip().lstrip("/")
    parts = PurePosixPath(value).parts
    if not value or value.endswith("/") or ".." in parts:
        raise ValueError("Invalid document key.")
    if not any(value.startswith(prefix) for prefix in allowed_prefixes):
        raise ValueError("Document key is outside the allowed prefixes.")
    return value


def _validate_upload_prefix(prefix):
    value = _normalize_prefix(prefix)
    parts = PurePosixPath(value).parts
    if ".." in parts or not value.startswith(DOCUMENTS_PREFIX):
        raise ValueError("Upload prefix must be inside documents/.")
    return value


def _safe_filename(filename):
    name = os.path.basename((filename or "").replace("\\", "/")).strip()
    if not name or name in {".", ".."}:
        raise ValueError("Invalid file name.")
    if any(char in name for char in ("\x00", "/", "\\")):
        raise ValueError("File name contains invalid characters.")
    return name


def _validate_extension(filename):
    extension = PurePosixPath(filename).suffix.lower()
    if extension in BLOCKED_EXTENSIONS:
        raise ValueError("This file type is not allowed.")
    if extension and extension not in ALLOWED_EXTENSIONS:
        raise ValueError("This file extension is not supported.")
    if not extension:
        raise ValueError("Files must include an extension.")


def _object_payload(obj):
    key = obj.get("Key", "")
    return {
        "key": key,
        "name": PurePosixPath(key).name,
        "folder": str(PurePosixPath(key).parent),
        "size": obj.get("Size", 0),
        "lastModified": obj.get("LastModified").isoformat()
        if obj.get("LastModified")
        else None,
        "storageClass": obj.get("StorageClass"),
    }


class CheckComplianceDocumentListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        bucket = _bucket_name()
        if not bucket:
            return Response(
                {"detail": "Compliance documents bucket is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        prefix = DOCUMENTS_PREFIX
        s3 = _s3_client()

        try:
            paginator = s3.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
            documents = []
            for page in pages:
                for obj in page.get("Contents", []):
                    if obj.get("Key", "").endswith("/"):
                        continue
                    documents.append(_object_payload(obj))
        except ClientError as exc:
            return Response(
                {"detail": "Error listing compliance documents.", "error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        documents.sort(key=lambda item: item["key"].lower())
        return Response(
            {
                "bucket": bucket,
                "prefix": prefix,
                "documents": documents,
            }
        )


class CheckComplianceDocumentUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        bucket = _bucket_name()
        if not bucket:
            return Response(
                {"detail": "Compliance documents bucket is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        files = request.FILES.getlist("file")
        if not files:
            return Response(
                {"detail": 'No file provided. Use field "file".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            prefix = _validate_upload_prefix(request.data.get("prefix"))
            upload_items = []
            for file_obj in files:
                filename = _safe_filename(file_obj.name)
                _validate_extension(filename)
                key = _validate_key(f"{prefix}{filename}", [DOCUMENTS_PREFIX])
                upload_items.append((file_obj, filename, key))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        s3 = _s3_client()
        results = []
        for file_obj, filename, key in upload_items:
            try:
                s3.upload_fileobj(
                    file_obj,
                    bucket,
                    key,
                    ExtraArgs={
                        "ContentType": file_obj.content_type
                        or "application/octet-stream",
                        "Metadata": {
                            "uploaded-by": str(request.user.pk),
                            "original-filename": filename,
                        },
                    },
                )
                results.append({"key": key, "name": filename, "status": "uploaded"})
            except ClientError as exc:
                results.append(
                    {
                        "key": key,
                        "name": filename,
                        "status": "error",
                        "error": str(exc),
                    }
                )

        all_uploaded = all(item["status"] == "uploaded" for item in results)
        return Response(
            {"results": results},
            status=status.HTTP_201_CREATED
            if all_uploaded
            else status.HTTP_207_MULTI_STATUS,
        )


class CheckComplianceDocumentDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        return _permanently_delete_document(request)


class CheckComplianceDocumentDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        bucket = _bucket_name()
        if not bucket:
            return Response(
                {"detail": "Compliance documents bucket is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            key = _validate_key(
                request.data.get("key"),
                [DOCUMENTS_PREFIX],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        s3 = _s3_client()
        try:
            url = s3.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": bucket,
                    "Key": key,
                    "ResponseContentDisposition": (
                        f'attachment; filename="{PurePosixPath(key).name}"'
                    ),
                },
                ExpiresIn=300,
            )
        except ClientError as exc:
            return Response(
                {"detail": "Error generating document download URL.", "error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({"url": url, "expiresIn": 300})


class CheckComplianceDocumentPermanentDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        return _permanently_delete_document(request)


class CheckComplianceDocumentRestoreView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        return Response(
            {"detail": "Compliance documents trash flow is disabled."},
            status=status.HTTP_410_GONE,
        )


def _permanently_delete_document(request):
    bucket = _bucket_name()
    if not bucket:
        return Response(
            {"detail": "Compliance documents bucket is not configured."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    try:
        key = _validate_key(request.data.get("key"), [DOCUMENTS_PREFIX])
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    s3 = _s3_client()
    try:
        s3.delete_object(Bucket=bucket, Key=key)
    except ClientError as exc:
        return Response(
            {"detail": "Error permanently deleting compliance document.", "error": str(exc)},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    return Response({"key": key, "status": "permanently_deleted"})
