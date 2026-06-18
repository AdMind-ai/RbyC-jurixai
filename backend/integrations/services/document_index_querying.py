import logging

from django.db import DatabaseError, connection
from django.db.models import Q
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

from integrations.models import DocumentIndex
from integrations.services.document_index_search import (
    is_scope_query_term,
    normalize_search_value,
    search_variants,
)


logger = logging.getLogger(__name__)


def parse_csv_query_values(value: str) -> list[str]:
    return [
        item.strip()
        for item in (value or "").split(",")
        if item and item.strip()
    ]


def build_document_search_filter(term: str, include_preview: bool = False) -> Q:
    return build_document_search_filter_for_mode(
        term,
        include_preview=include_preview,
        include_extended_text=True,
    )


def build_document_search_filter_for_mode(
    term: str,
    *,
    include_preview: bool = False,
    include_extended_text: bool = True,
) -> Q:
    search_filter = Q()
    for variant in search_variants(term):
        variant_filter = (
            Q(filename__icontains=variant)
            | Q(object_key__icontains=variant)
            | Q(document_type__icontains=variant)
            | Q(document_family__icontains=variant)
            | Q(topic_tags__icontains=variant)
            | Q(control_function_tags__icontains=variant)
            | Q(year__icontains=variant)
        )
        if include_extended_text:
            variant_filter |= (
                Q(search_text__icontains=variant)
                | Q(extracted_text__icontains=variant)
            )
        search_filter |= variant_filter
        if include_preview:
            search_filter |= Q(text_preview__icontains=variant)
    return search_filter


def can_use_postgres_fts() -> bool:
    return connection.vendor == "postgresql"


def build_document_search_query_text(raw_query: str, query_terms: list[str]) -> str:
    effective_terms = query_terms_for_filtering(query_terms)
    cleaned_terms = [
        " ".join((term or "").split())
        for term in effective_terms
        if " ".join((term or "").split())
    ]
    if cleaned_terms:
        return " ".join(cleaned_terms)
    return " ".join((raw_query or "").split())


def query_terms_for_filtering(query_terms: list[str]) -> list[str]:
    anchor_terms = [
        term for term in query_terms if term and not is_scope_query_term(term)
    ]
    return anchor_terms or query_terms


def high_precision_query_terms(query_terms: list[str]) -> list[str]:
    anchor_terms = query_terms_for_filtering(query_terms)
    phrase_terms = [term for term in anchor_terms if " " in normalize_search_value(term)]
    if not phrase_terms:
        return []

    precision_terms = []
    for phrase in phrase_terms:
        normalized_phrase = normalize_search_value(phrase)
        if normalized_phrase and normalized_phrase not in precision_terms:
            precision_terms.append(normalized_phrase)
        for token in normalized_phrase.split():
            if 2 < len(token) <= 3 and token not in precision_terms:
                precision_terms.append(token)
    return precision_terms


def document_matches_any_query_term(document: DocumentIndex, query_terms: list[str]) -> bool:
    if not query_terms:
        return True

    combined_text = normalize_search_value(
        " ".join(
            [
                document.filename or "",
                document.object_key or "",
                document.document_type or "",
                document.document_family or "",
                document.topic_tags or "",
                document.control_function_tags or "",
                document.year or "",
                document.text_preview or "",
                getattr(document, "search_text", "") or "",
                getattr(document, "extracted_text", "") or "",
            ]
        )
    )
    for term in query_terms:
        for variant in search_variants(term):
            normalized_variant = normalize_search_value(variant)
            if normalized_variant and normalized_variant in combined_text:
                return True
    return False


def compute_postgres_fts_candidate_limit(limit: int) -> int:
    normalized_limit = max(1, limit)
    candidate_limit = max(normalized_limit * 2, 30)
    return min(candidate_limit, 80)


def build_document_index_queryset(customer_code: str, *, include_extended_text: bool):
    only_fields = [
        "object_key",
        "filename",
        "extension",
        "size_bytes",
        "s3_last_modified",
        "last_modified",
        "document_date",
        "year",
        "document_type",
        "document_family",
        "control_function_tags",
        "topic_tags",
        "text_preview",
        "indexed_at",
        "client__customer_code",
        "client__active",
    ]
    if include_extended_text:
        only_fields.extend(["search_text", "extracted_text"])

    return DocumentIndex.objects.select_related("client").filter(
        client__customer_code=customer_code,
        client__active=True,
        active=True,
    ).only(*only_fields)


def search_documents_with_postgres_fts(
    *,
    documents,
    raw_query: str,
    query_terms: list[str],
    sort_by: str,
    sort_order: str,
    limit: int,
) -> list[DocumentIndex] | None:
    if not can_use_postgres_fts():
        return None

    search_query_text = build_document_search_query_text(raw_query, query_terms)
    if not search_query_text:
        return None

    candidate_limit = compute_postgres_fts_candidate_limit(limit)
    fallback_order_fields = {
        "last_modified": "s3_last_modified",
        "s3_last_modified": "s3_last_modified",
        "document_date": "document_date",
        "size": "size_bytes",
        "filename": "filename",
    }
    fallback_order_field = fallback_order_fields.get(sort_by, "s3_last_modified")
    if sort_order != "asc":
        fallback_order_field = f"-{fallback_order_field}"

    try:
        search_vector = (
            SearchVector("filename", weight="A", config="simple")
            + SearchVector("object_key", weight="A", config="simple")
            + SearchVector("document_family", weight="B", config="simple")
            + SearchVector("document_type", weight="B", config="simple")
            + SearchVector("topic_tags", weight="B", config="simple")
            + SearchVector("control_function_tags", weight="C", config="simple")
            + SearchVector("search_text", weight="C", config="simple")
            + SearchVector("text_preview", weight="D", config="simple")
        )
        search_query = SearchQuery(
            search_query_text,
            config="simple",
            search_type="websearch",
        )
        ranked_documents = list(
            documents.annotate(
                fts_rank=SearchRank(search_vector, search_query),
            )
            .filter(fts_rank__gt=0)
            .order_by("-fts_rank", fallback_order_field, "-indexed_at")[:candidate_limit]
        )
    except DatabaseError as exc:
        logger.warning(
            "[document_index] postgres_fts_unavailable error=%s query=%s",
            exc,
            search_query_text or "<empty>",
        )
        return None

    if ranked_documents:
        logger.info(
            "[document_index] postgres_fts_completed query=%s returned_documents=%s candidate_limit=%s top_rank=%s",
            search_query_text or "<empty>",
            len(ranked_documents),
            candidate_limit,
            getattr(ranked_documents[0], "fts_rank", 0),
        )
    return ranked_documents


def merge_document_candidates(
    primary_documents: list[DocumentIndex],
    secondary_documents: list[DocumentIndex],
) -> list[DocumentIndex]:
    merged_documents = []
    seen_ids = set()
    for document in [*primary_documents, *secondary_documents]:
        document_id = getattr(document, "pk", None) or id(document)
        if document_id in seen_ids:
            continue
        seen_ids.add(document_id)
        merged_documents.append(document)
    return merged_documents


def build_broad_query_filter(query_terms: list[str], *, include_extended_text: bool) -> Q:
    broad_filter = Q()
    for term in query_terms:
        broad_filter |= build_document_search_filter_for_mode(
            term,
            include_preview=True,
            include_extended_text=include_extended_text,
        )
    return broad_filter


def search_documents_in_index(
    *,
    raw_query: str,
    customer_code: str,
    year: str,
    document_type: str,
    document_family: str,
    control_function_tags: str,
    topic_tags: str,
    extension: str,
    filename_contains: str,
    path_contains: str,
    sort_by: str,
    sort_order: str,
    limit: int,
    query_terms: list[str],
    include_extended_text: bool,
) -> list[DocumentIndex]:
    documents = build_document_index_queryset(
        customer_code,
        include_extended_text=include_extended_text,
    )

    if year:
        documents = documents.filter(year=year)

    if document_type:
        document_type_filter = Q()
        for raw_value in parse_csv_query_values(document_type) or [document_type]:
            for variant in search_variants(raw_value):
                document_type_filter |= Q(document_type__icontains=variant)
        documents = documents.filter(document_type_filter)

    if document_family:
        document_family_filter = Q()
        for raw_value in parse_csv_query_values(document_family) or [document_family]:
            for variant in search_variants(raw_value):
                document_family_filter |= Q(document_family__icontains=variant)
        documents = documents.filter(document_family_filter)

    if control_function_tags:
        control_function_filter = Q()
        for raw_value in parse_csv_query_values(control_function_tags) or [control_function_tags]:
            for variant in search_variants(raw_value):
                control_function_filter |= Q(control_function_tags__icontains=variant)
        documents = documents.filter(control_function_filter)

    if topic_tags:
        topic_filter = Q()
        for raw_value in parse_csv_query_values(topic_tags) or [topic_tags]:
            for variant in search_variants(raw_value):
                topic_filter |= Q(topic_tags__icontains=variant)
        documents = documents.filter(topic_filter)

    if extension:
        normalized_extension = extension if extension.startswith(".") else f".{extension}"
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

    order_fields = {
        "last_modified": "s3_last_modified",
        "s3_last_modified": "s3_last_modified",
        "document_date": "document_date",
        "size": "size_bytes",
        "filename": "filename",
    }
    order_field = order_fields.get(sort_by, "s3_last_modified")
    if sort_order != "asc":
        order_field = f"-{order_field}"

    if query_terms:
        filter_query_terms = query_terms_for_filtering(query_terms)
        precision_query_terms = high_precision_query_terms(query_terms)
        if include_extended_text:
            fts_documents = search_documents_with_postgres_fts(
                documents=documents,
                raw_query=raw_query,
                query_terms=filter_query_terms,
                sort_by=sort_by,
                sort_order=sort_order,
                limit=limit,
            )
            if fts_documents:
                if precision_query_terms:
                    fts_documents = [
                        document
                        for document in fts_documents
                        if document_matches_any_query_term(
                            document,
                            precision_query_terms,
                        )
                    ]
                if fts_documents:
                    fallback_filter = build_broad_query_filter(
                        precision_query_terms or filter_query_terms,
                        include_extended_text=include_extended_text,
                    )
                    fallback_documents = list(
                        documents.filter(fallback_filter)
                        .order_by(order_field, "-indexed_at")[:limit]
                    )
                    return merge_document_candidates(
                        fts_documents,
                        fallback_documents,
                    )

        strict_documents = documents
        for term in filter_query_terms:
            strict_documents = strict_documents.filter(
                build_document_search_filter_for_mode(
                    term,
                    include_extended_text=include_extended_text,
                )
            )

        if strict_documents.exists() or len(filter_query_terms) == 1:
            documents = strict_documents
        else:
            broad_filter = build_broad_query_filter(
                precision_query_terms or filter_query_terms,
                include_extended_text=include_extended_text,
            )
            documents = documents.filter(broad_filter)

    return list(documents.order_by(order_field, "-indexed_at")[:limit])
