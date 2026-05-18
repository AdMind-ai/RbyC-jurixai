from django.utils import timezone

from integrations.models import DocumentIndex
from integrations.services.document_search_index import refresh_document_search_text


def apply_document_index_content_update(
    document: DocumentIndex,
    *,
    text_preview: str,
    extracted_text: str,
) -> dict[str, object]:
    normalized_preview = text_preview[:6000]
    normalized_extracted_text = extracted_text[:30000]
    source_text = normalized_extracted_text or normalized_preview

    update_fields = ["updated_at"]
    if normalized_preview and document.text_preview != normalized_preview:
        document.text_preview = normalized_preview
        update_fields.append("text_preview")
    if normalized_extracted_text and document.extracted_text != normalized_extracted_text:
        document.extracted_text = normalized_extracted_text
        update_fields.append("extracted_text")

    control_function_tags = DocumentIndex.infer_control_function_tags(
        document.object_key,
        source_text,
    )
    topic_tags = DocumentIndex.infer_topic_tags(
        document.object_key,
        source_text,
    )
    if document.control_function_tags != control_function_tags:
        document.control_function_tags = control_function_tags
        update_fields.append("control_function_tags")
    if document.topic_tags != topic_tags:
        document.topic_tags = topic_tags
        update_fields.append("topic_tags")
    if refresh_document_search_text(document):
        update_fields.append("search_text")
    if document.extraction_status != DocumentIndex.STATUS_READY:
        document.extraction_status = DocumentIndex.STATUS_READY
        update_fields.append("extraction_status")
    if document.extraction_error:
        document.extraction_error = ""
        update_fields.append("extraction_error")

    document.indexed_at = timezone.now()
    update_fields.append("indexed_at")
    document.save(update_fields=update_fields)

    return {
        "normalized_preview": normalized_preview,
        "normalized_extracted_text": normalized_extracted_text,
        "update_fields": update_fields,
    }
