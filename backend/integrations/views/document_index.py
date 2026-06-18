import logging
from time import perf_counter

from django.db import DatabaseError
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView

from integrations.models import DocumentIndex
from integrations.services.document_index_auth import (
    resolve_internal_document_index_customer_code,
    validate_internal_document_index_request,
)
from integrations.services.document_index_content import apply_document_index_content_update
from integrations.services.document_index_excerpt import build_document_matched_excerpt
from integrations.services.document_index_search import (
    query_terms_for_search,
    search_variants,
)
from integrations.services.document_index_http import (
    build_index_request_debug_context,
    parse_document_index_request_params,
    serialize_document_index_documents,
)
from integrations.services.document_index_logging import (
    log_document_index_request_completed,
    log_document_index_search_result,
)
from integrations.services.document_index_ranking import (
    score_document_match,
    score_fts_alignment,
    sort_documents_by_relevance,
)
from integrations.services.document_index_querying import (
    build_document_search_filter,
    build_document_search_filter_for_mode,
    build_document_search_query_text,
    can_use_postgres_fts,
    compute_postgres_fts_candidate_limit,
    search_documents_in_index,
)


logger = logging.getLogger(__name__)


@extend_schema(exclude=True)
class InternalDocumentIndexView(APIView):
    authentication_classes = []
    permission_classes = []

    class OutputSerializer(serializers.Serializer):
        key = serializers.CharField()
        filename = serializers.CharField()
        extension = serializers.CharField(allow_blank=True)
        size_bytes = serializers.IntegerField()
        s3_last_modified = serializers.DateTimeField(allow_null=True)
        last_modified = serializers.DateTimeField(allow_null=True)
        document_date = serializers.DateField(allow_null=True)
        path = serializers.CharField()
        year = serializers.CharField(allow_blank=True)
        document_type = serializers.CharField()
        document_family = serializers.CharField()
        control_function_tags = serializers.CharField(allow_blank=True)
        topic_tags = serializers.CharField(allow_blank=True)
        text_preview = serializers.CharField(allow_blank=True)
        matched_excerpt = serializers.CharField(allow_blank=True)

    def get(self, request):
        started_at = perf_counter()
        try:
            customer_code = validate_internal_document_index_request(request)
        except AuthenticationFailed as exc:
            return Response(
                {"detail": str(exc.detail)},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        params = parse_document_index_request_params(request)
        query_terms = query_terms_for_search(params.query)
        request_debug = build_index_request_debug_context(
            customer_code=customer_code,
            query=params.query,
            year=params.year,
            document_type=params.document_type,
            document_family=params.document_family,
            control_function_tags=params.control_function_tags,
            topic_tags=params.topic_tags,
            extension=params.extension,
            filename_contains=params.filename_contains,
            path_contains=params.path_contains,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
            limit=params.limit,
        )
        try:
            try:
                documents = search_documents_in_index(
                    raw_query=params.query,
                    customer_code=customer_code,
                    year=params.year,
                    document_type=params.document_type,
                    document_family=params.document_family,
                    control_function_tags=params.control_function_tags,
                    topic_tags=params.topic_tags,
                    extension=params.extension,
                    filename_contains=params.filename_contains,
                    path_contains=params.path_contains,
                    sort_by=params.sort_by,
                    sort_order=params.sort_order,
                    limit=params.limit,
                    query_terms=query_terms,
                    include_extended_text=True,
                )
            except DatabaseError as exc:
                logger.warning(
                    "[document_index] extended_search_unavailable customer_code=%s error=%s request=%s",
                    customer_code,
                    exc,
                    request_debug,
                )
                documents = search_documents_in_index(
                    raw_query=params.query,
                    customer_code=customer_code,
                    year=params.year,
                    document_type=params.document_type,
                    document_family=params.document_family,
                    control_function_tags=params.control_function_tags,
                    topic_tags=params.topic_tags,
                    extension=params.extension,
                    filename_contains=params.filename_contains,
                    path_contains=params.path_contains,
                    sort_by=params.sort_by,
                    sort_order=params.sort_order,
                    limit=params.limit,
                    query_terms=query_terms,
                    include_extended_text=False,
                )
        except Exception:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            logger.exception(
                "[document_index] request_failed duration_ms=%s request=%s",
                duration_ms,
                request_debug,
            )
            raise

        documents = sort_documents_by_relevance(documents, query_terms)
        for document in documents:
            document.relevance_score = score_document_match(document, query_terms)
            document.matched_excerpt = build_document_matched_excerpt(
                document,
                query_terms,
            )
        payload = serialize_document_index_documents(documents)

        log_document_index_search_result(
            logger,
            query=params.query,
            query_terms=query_terms,
            documents=documents,
        )

        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        log_document_index_request_completed(
            logger,
            duration_ms=duration_ms,
            customer_code=customer_code,
            returned_documents=len(payload),
            limit=params.limit,
            query=params.query,
            year=params.year,
            document_type=params.document_type,
            document_family=params.document_family,
            control_function_tags=params.control_function_tags,
            topic_tags=params.topic_tags,
            extension=params.extension,
            filename_contains=params.filename_contains,
            path_contains=params.path_contains,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
        )
        return JsonResponse(payload, safe=False)


@extend_schema(exclude=True)
class InternalDocumentIndexContentView(APIView):
    authentication_classes = []
    permission_classes = []

    class InputSerializer(serializers.Serializer):
        key = serializers.CharField()
        text_preview = serializers.CharField(required=False, allow_blank=True, default="")
        extracted_text = serializers.CharField(required=False, allow_blank=True, default="")

    def post(self, request):
        started_at = perf_counter()
        try:
            customer_code = validate_internal_document_index_request(request)
        except AuthenticationFailed as exc:
            return Response(
                {"detail": str(exc.detail)},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        object_key = serializer.validated_data["key"].strip()
        text_preview = (serializer.validated_data.get("text_preview") or "").strip()
        extracted_text = (serializer.validated_data.get("extracted_text") or "").strip()

        if not object_key:
            return Response(
                {"detail": "Document key is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        document = DocumentIndex.objects.select_related("client").filter(
            client__customer_code=customer_code,
            client__active=True,
            active=True,
            object_key=object_key,
        ).first()
        if document is None:
            return Response(
                {"detail": "Document not found for MCP content update."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            update_result = apply_document_index_content_update(
                document,
                text_preview=text_preview,
                extracted_text=extracted_text,
            )
        except Exception:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            logger.exception(
                "[document_index] content_update_failed duration_ms=%s customer_code=%s key=%s preview_chars=%s extracted_chars=%s",
                duration_ms,
                customer_code,
                object_key,
                len(text_preview or ""),
                len(extracted_text or ""),
            )
            raise

        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        logger.info(
            "[document_index] content_update_completed duration_ms=%s customer_code=%s key=%s preview_chars=%s extracted_chars=%s",
            duration_ms,
            customer_code,
            object_key,
            len(update_result["normalized_preview"]),
            len(update_result["normalized_extracted_text"]),
        )
        return Response({"status": "ok"})
