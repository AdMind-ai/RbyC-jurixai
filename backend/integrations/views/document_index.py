import logging
import unicodedata
from time import perf_counter

from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from integrations.models import DocumentIndex


logger = logging.getLogger(__name__)


def normalize_search_value(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    normalized = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return " ".join(normalized.casefold().split())


def search_variants(value: str) -> list[str]:
    cleaned = " ".join((value or "").strip().split())
    normalized = normalize_search_value(cleaned)
    variants = []
    for item in [cleaned, normalized]:
        if item and item not in variants:
            variants.append(item)
    return variants


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
        started_at = perf_counter()
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
        ).only(
            "object_key",
            "filename",
            "extension",
            "size_bytes",
            "last_modified",
            "year",
            "document_type",
            "text_preview",
            "indexed_at",
            "client__customer_code",
            "client__active",
        )

        if year:
            documents = documents.filter(year=year)

        if extension:
            normalized_extension = (
                extension if extension.startswith(".") else f".{extension}"
            )
            documents = documents.filter(extension=normalized_extension)

        if filename_contains:
            filename_filter = Q()
            for variant in search_variants(filename_contains):
                filename_filter |= Q(filename__icontains=variant)
            documents = documents.filter(filename_filter)

        if path_contains:
            path_filter = Q()
            for variant in search_variants(path_contains):
                path_filter |= Q(object_key__icontains=variant)
            documents = documents.filter(path_filter)

        if query:
            for term in [item for item in query.split() if item][:6]:
                term_filter = Q()
                for variant in search_variants(term):
                    term_filter |= (
                        Q(filename__icontains=variant)
                        | Q(object_key__icontains=variant)
                        | Q(document_type__icontains=variant)
                        | Q(year__icontains=variant)
                    )
                documents = documents.filter(
                    term_filter
                )

        order_fields = {
            "last_modified": "last_modified",
            "size": "size_bytes",
            "filename": "filename",
        }
        order_field = order_fields.get(sort_by, "last_modified")
        if sort_order != "asc":
            order_field = f"-{order_field}"

        documents = list(documents.order_by(order_field, "-indexed_at")[:limit])
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

        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        logger.info(
            "[document_index] request_completed duration_ms=%s customer_code=%s returned_documents=%s limit=%s query=%s year=%s extension=%s filename_contains=%s path_contains=%s sort_by=%s sort_order=%s",
            duration_ms,
            customer_code,
            len(payload),
            limit,
            query or "<empty>",
            year or "<empty>",
            extension or "<empty>",
            filename_contains or "<empty>",
            path_contains or "<empty>",
            sort_by,
            sort_order,
        )
        return JsonResponse(payload, safe=False)
