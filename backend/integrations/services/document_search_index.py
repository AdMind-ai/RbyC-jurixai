from integrations.models import DocumentIndex


def build_document_search_text(document: DocumentIndex) -> str:
    """
    Build a normalized search corpus that can be reused by the current
    DB-agnostic retrieval and later serve as the input source for Postgres FTS.
    """
    parts = [
        (document.filename or "").strip(),
        (document.object_key or "").strip(),
        (document.document_family or "").strip(),
        (document.document_type or "").strip(),
        (document.topic_tags or "").strip().replace(",", " "),
        (document.control_function_tags or "").strip().replace(",", " "),
        (document.year or "").strip(),
        (document.text_preview or "").strip(),
        (document.extracted_text or "").strip(),
    ]
    return "\n".join(part for part in parts if part).strip()


def refresh_document_search_text(document: DocumentIndex) -> bool:
    updated_value = build_document_search_text(document)
    if document.search_text == updated_value:
        return False
    document.search_text = updated_value
    return True
