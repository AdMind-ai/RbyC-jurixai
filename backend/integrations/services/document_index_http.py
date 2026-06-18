from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentIndexRequestParams:
    query: str
    year: str
    document_type: str
    document_family: str
    control_function_tags: str
    topic_tags: str
    extension: str
    filename_contains: str
    path_contains: str
    sort_by: str
    sort_order: str
    limit: int


def build_index_request_debug_context(
    *,
    customer_code: str,
    query: str = "",
    year: str = "",
    document_type: str = "",
    document_family: str = "",
    control_function_tags: str = "",
    topic_tags: str = "",
    extension: str = "",
    filename_contains: str = "",
    path_contains: str = "",
    sort_by: str = "",
    sort_order: str = "",
    limit: int | None = None,
) -> dict[str, str | int]:
    return {
        "customer_code": customer_code or "<empty>",
        "query": query or "<empty>",
        "year": year or "<empty>",
        "document_type": document_type or "<empty>",
        "document_family": document_family or "<empty>",
        "control_function_tags": control_function_tags or "<empty>",
        "topic_tags": topic_tags or "<empty>",
        "extension": extension or "<empty>",
        "filename_contains": filename_contains or "<empty>",
        "path_contains": path_contains or "<empty>",
        "sort_by": sort_by or "<empty>",
        "sort_order": sort_order or "<empty>",
        "limit": limit or 0,
    }


def parse_document_index_request_params(request) -> DocumentIndexRequestParams:
    try:
        limit = int(request.query_params.get("limit") or 200)
    except (TypeError, ValueError):
        limit = 200
    limit = max(1, min(limit, 300))

    return DocumentIndexRequestParams(
        query=(request.query_params.get("query") or "").strip(),
        year=(request.query_params.get("year") or "").strip(),
        document_type=(request.query_params.get("document_type") or "").strip(),
        document_family=(request.query_params.get("document_family") or "").strip(),
        control_function_tags=(
            request.query_params.get("control_function_tags") or ""
        ).strip(),
        topic_tags=(request.query_params.get("topic_tags") or "").strip(),
        extension=(request.query_params.get("extension") or "").strip().lower(),
        filename_contains=(request.query_params.get("filename_contains") or "").strip(),
        path_contains=(request.query_params.get("path_contains") or "").strip(),
        sort_by=(request.query_params.get("sort_by") or "last_modified").strip(),
        sort_order=(request.query_params.get("sort_order") or "desc").strip(),
        limit=limit,
    )


def serialize_document_index_documents(documents: list) -> list[dict[str, object]]:
    return [
        {
            "key": document.object_key,
            "filename": document.filename,
            "extension": document.extension,
            "size_bytes": document.size_bytes,
            "s3_last_modified": document.s3_last_modified or document.last_modified,
            "last_modified": document.s3_last_modified or document.last_modified,
            "document_date": document.document_date,
            "path": document.object_key,
            "year": document.year,
            "document_type": document.document_type,
            "document_family": document.document_family,
            "control_function_tags": document.control_function_tags,
            "topic_tags": document.topic_tags,
            "text_preview": document.text_preview,
            "matched_excerpt": getattr(document, "matched_excerpt", ""),
            "relevance_score": getattr(document, "relevance_score", 0),
        }
        for document in documents
    ]

