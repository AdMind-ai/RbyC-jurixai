from django.conf import settings
from django.db.models import Q
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from integrations.models import DocumentIndex


class InternalDocumentIndexView(APIView):
    authentication_classes = []
    permission_classes = []

    class OutputSerializer(serializers.Serializer):
        key = serializers.CharField()
        filename = serializers.CharField()
        extension = serializers.CharField(allow_blank=True)
        size_bytes = serializers.IntegerField()
        last_modified = serializers.DateTimeField(allow_null=True)
        path = serializers.CharField()
        year = serializers.CharField(allow_blank=True)
        document_type = serializers.CharField()
        text_preview = serializers.CharField(allow_blank=True)

    def get(self, request):
        expected_key = getattr(settings, "DOCUMENT_INDEX_API_KEY", None)
        provided_key = request.headers.get("X-Internal-API-Key")
        if not expected_key or provided_key != expected_key:
            return Response(
                {"detail": "Unauthorized internal document index request."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        customer_code = (
            request.query_params.get("customer_code")
            or getattr(settings, "DOCUMENT_INDEX_CUSTOMER_CODE", "default")
        )
        query = (request.query_params.get("query") or "").strip()
        year = (request.query_params.get("year") or "").strip()
        extension = (request.query_params.get("extension") or "").strip().lower()
        filename_contains = (
            request.query_params.get("filename_contains") or ""
        ).strip()
        path_contains = (request.query_params.get("path_contains") or "").strip()
        sort_by = (request.query_params.get("sort_by") or "last_modified").strip()
        sort_order = (request.query_params.get("sort_order") or "desc").strip()

        try:
            limit = int(request.query_params.get("limit") or 200)
        except (TypeError, ValueError):
            limit = 200
        limit = max(1, min(limit, 300))

        documents = DocumentIndex.objects.select_related("client").filter(
            client__customer_code=customer_code,
            client__active=True,
            active=True,
        )

        if year:
            documents = documents.filter(year=year)

        if extension:
            normalized_extension = (
                extension if extension.startswith(".") else f".{extension}"
            )
            documents = documents.filter(extension=normalized_extension)

        if filename_contains:
            documents = documents.filter(filename__icontains=filename_contains)

        if path_contains:
            documents = documents.filter(object_key__icontains=path_contains)

        if query:
            for term in [item for item in query.split() if item]:
                documents = documents.filter(
                    Q(filename__icontains=term)
                    | Q(object_key__icontains=term)
                    | Q(document_type__icontains=term)
                    | Q(text_preview__icontains=term)
                )

        order_fields = {
            "last_modified": "last_modified",
            "size": "size_bytes",
            "filename": "filename",
        }
        order_field = order_fields.get(sort_by, "last_modified")
        if sort_order != "asc":
            order_field = f"-{order_field}"

        documents = documents.order_by(order_field, "-indexed_at")[:limit]
        payload = [
            {
                "key": document.object_key,
                "filename": document.filename,
                "extension": document.extension,
                "size_bytes": document.size_bytes,
                "last_modified": document.last_modified,
                "path": document.object_key,
                "year": document.year,
                "document_type": document.document_type,
                "text_preview": document.text_preview,
            }
            for document in documents
        ]

        serializer = self.OutputSerializer(payload, many=True)
        return Response(serializer.data)
