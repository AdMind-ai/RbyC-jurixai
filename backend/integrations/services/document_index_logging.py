import logging

from integrations.services.document_index_ranking import (
    build_document_ranking_debug,
    build_query_profile,
)


def log_document_index_search_result(
    logger: logging.Logger,
    *,
    query: str,
    query_terms: list[str],
    documents: list,
) -> None:
    if not documents:
        return

    ranking_debug = build_document_ranking_debug(documents[0], query_terms)
    query_profile = build_query_profile(query_terms)
    logger.info(
        "[document_index] ranking_top_result query=%s filename=%s key=%s relevance_score=%s document_date=%s s3_last_modified=%s",
        query or "<empty>",
        ranking_debug["filename"] or "<empty>",
        ranking_debug["key"] or "<empty>",
        ranking_debug["relevance_score"],
        ranking_debug["document_date"] or "<empty>",
        ranking_debug["s3_last_modified"] or "<empty>",
    )
    if query_profile.get("needs_approval_evidence"):
        logger.info(
            "[document_index] approval_evidence_requires_document_content query=%s filename=%s document_date=%s s3_last_modified=%s",
            query or "<empty>",
            documents[0].filename or "<empty>",
            (
                documents[0].document_date.isoformat()
                if documents[0].document_date
                else "<empty>"
            ),
            (
                documents[0].s3_last_modified.isoformat()
                if documents[0].s3_last_modified
                else (
                    documents[0].last_modified.isoformat()
                    if documents[0].last_modified
                    else "<empty>"
                )
            ),
        )


def log_document_index_request_completed(
    logger: logging.Logger,
    *,
    duration_ms: float,
    customer_code: str,
    returned_documents: int,
    limit: int,
    query: str,
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
) -> None:
    logger.info(
        "[document_index] request_completed duration_ms=%s customer_code=%s returned_documents=%s limit=%s query=%s year=%s document_type=%s document_family=%s control_function_tags=%s topic_tags=%s extension=%s filename_contains=%s path_contains=%s sort_by=%s sort_order=%s",
        duration_ms,
        customer_code,
        returned_documents,
        limit,
        query or "<empty>",
        year or "<empty>",
        document_type or "<empty>",
        document_family or "<empty>",
        control_function_tags or "<empty>",
        topic_tags or "<empty>",
        extension or "<empty>",
        filename_contains or "<empty>",
        path_contains or "<empty>",
        sort_by,
        sort_order,
    )
