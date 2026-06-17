import logging
import os
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field

from django.utils import timezone

from core.utils.s3_utils import _get_s3_client
from integrations.models import DocumentIndex
from integrations.services.document_search_index import refresh_document_search_text


logger = logging.getLogger(__name__)

DEFAULT_PREVIEW_CHARS = int(os.environ.get("DOCUMENT_INDEX_PREVIEW_CHARS", "6000"))
DEFAULT_MAX_FILE_BYTES = int(
    os.environ.get("DOCUMENT_INDEX_PREVIEW_MAX_FILE_BYTES", str(8 * 1024 * 1024))
)
DEFAULT_MAX_PDF_PAGES = int(os.environ.get("DOCUMENT_INDEX_PREVIEW_PDF_PAGES", "3"))


@dataclass
class DocumentPreviewResult:
    processed_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    batch_count: int = 0
    attempted_ids: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class DocumentExtractedContent:
    text_preview: str
    extracted_text: str


DEFAULT_SEARCH_TEXT_CHARS = int(
    os.environ.get("DOCUMENT_INDEX_SEARCH_TEXT_CHARS", "120000")
)


def build_missing_document_previews(
    customer_code: str = "",
    filename_contains: str = "",
    path_contains: str = "",
    document_type: str = "",
    year: str = "",
    limit: int = 100,
    force: bool = False,
    exclude_ids: set[int] | None = None,
) -> DocumentPreviewResult:
    documents = DocumentIndex.objects.select_related("client").filter(
        active=True,
        client__active=True,
    )
    if customer_code:
        documents = documents.filter(client__customer_code=customer_code)
    if filename_contains:
        documents = documents.filter(filename__icontains=filename_contains)
    if path_contains:
        documents = documents.filter(object_key__icontains=path_contains)
    if document_type:
        documents = documents.filter(document_type=document_type)
    if year:
        documents = documents.filter(year=year)
    if not force:
        documents = documents.filter(extraction_status=DocumentIndex.STATUS_PENDING)
    if exclude_ids:
        documents = documents.exclude(id__in=exclude_ids)

    documents = documents.order_by("-document_date", "-s3_last_modified", "id")[
        : max(1, limit)
    ]
    s3_client = _get_s3_client()
    result = DocumentPreviewResult()
    result.batch_count = 1

    for document in documents:
        result.attempted_ids.append(document.id)
        try:
            content = extract_document_content(document, s3_client=s3_client)
            if content.text_preview or content.extracted_text:
                document.text_preview = content.text_preview
                document.extracted_text = content.extracted_text
                source_text = content.extracted_text or content.text_preview
                document.control_function_tags = (
                    DocumentIndex.infer_control_function_tags(
                        document.object_key,
                        source_text,
                    )
                )
                document.topic_tags = DocumentIndex.infer_topic_tags(
                    document.object_key,
                    source_text,
                )
                document.extraction_status = DocumentIndex.STATUS_READY
                document.extraction_error = ""
                result.processed_count += 1
            else:
                document.extraction_status = DocumentIndex.STATUS_SKIPPED
                document.extraction_error = "Preview not supported or empty."
                result.skipped_count += 1

            document.indexed_at = timezone.now()
            refresh_document_search_text(document)
            document.save(
                update_fields=[
                    "text_preview",
                    "extracted_text",
                    "search_text",
                    "control_function_tags",
                    "topic_tags",
                    "extraction_status",
                    "extraction_error",
                    "indexed_at",
                    "updated_at",
                ]
            )
        except Exception as exc:
            logger.exception(
                "[document_preview] failed object_key=%s",
                document.object_key,
            )
            document.extraction_status = DocumentIndex.STATUS_FAILED
            document.extraction_error = str(exc)
            document.save(
                update_fields=[
                    "extraction_status",
                    "extraction_error",
                    "updated_at",
                ]
            )
            result.failed_count += 1

    logger.info(
        "[document_preview] completed customer_code=%s processed=%s skipped=%s failed=%s",
        customer_code or "<all>",
        result.processed_count,
        result.skipped_count,
        result.failed_count,
    )
    return result


def build_document_previews_in_batches(
    customer_code: str = "",
    filename_contains: str = "",
    path_contains: str = "",
    document_type: str = "",
    year: str = "",
    batch_size: int = 100,
    force: bool = False,
    max_batches: int = 0,
) -> DocumentPreviewResult:
    aggregate = DocumentPreviewResult()
    seen_ids: set[int] = set()

    while True:
        if max_batches and aggregate.batch_count >= max_batches:
            break

        batch_result = build_missing_document_previews(
            customer_code=customer_code,
            filename_contains=filename_contains,
            path_contains=path_contains,
            document_type=document_type,
            year=year,
            limit=batch_size,
            force=force,
            exclude_ids=seen_ids,
        )
        if not batch_result.attempted_ids:
            break

        aggregate.processed_count += batch_result.processed_count
        aggregate.skipped_count += batch_result.skipped_count
        aggregate.failed_count += batch_result.failed_count
        aggregate.batch_count += 1
        aggregate.attempted_ids.extend(batch_result.attempted_ids)
        seen_ids.update(batch_result.attempted_ids)

    logger.info(
        "[document_preview] batched_completed customer_code=%s processed=%s skipped=%s failed=%s batches=%s attempted=%s",
        customer_code or "<all>",
        aggregate.processed_count,
        aggregate.skipped_count,
        aggregate.failed_count,
        aggregate.batch_count,
        len(aggregate.attempted_ids),
    )
    return aggregate


def extract_document_preview(document: DocumentIndex, s3_client=None) -> str:
    return extract_document_content(document, s3_client=s3_client).text_preview


def extract_document_content(
    document: DocumentIndex,
    s3_client=None,
) -> DocumentExtractedContent:
    if document.size_bytes > DEFAULT_MAX_FILE_BYTES:
        return DocumentExtractedContent(text_preview="", extracted_text="")

    extension = (document.extension or "").lower()
    if extension not in {".pdf", ".docx", ".pptx", ".txt", ".md", ".csv"}:
        return DocumentExtractedContent(text_preview="", extracted_text="")

    s3_client = s3_client or _get_s3_client()
    suffix = extension or ".tmp"
    temp_fd, temp_path = tempfile.mkstemp(suffix=suffix)
    os.close(temp_fd)
    try:
        with open(temp_path, "w+b") as tmp:
            s3_client.download_fileobj(document.bucket_name, document.object_key, tmp)
            tmp.flush()
            tmp.seek(0)
            if extension in {".txt", ".md", ".csv"}:
                extracted_text = tmp.read(DEFAULT_SEARCH_TEXT_CHARS * 2).decode(
                    "utf-8",
                    errors="replace",
                )
                preview = extracted_text
            else:
                preview = ""
                extracted_text = ""

        if extension == ".pdf":
            preview = _extract_pdf_preview(temp_path)
            extracted_text = preview
        elif extension == ".docx":
            extracted_text = _extract_docx_text(temp_path)
            preview = extracted_text
        elif extension == ".pptx":
            preview = _extract_pptx_preview(temp_path)
            extracted_text = preview
    finally:
        try:
            os.remove(temp_path)
        except FileNotFoundError:
            pass

    return DocumentExtractedContent(
        text_preview=_normalize_preview(preview),
        extracted_text=_normalize_extracted_text(extracted_text),
    )


def _extract_pdf_preview(filepath: str) -> str:
    from PyPDF2 import PdfReader

    reader = PdfReader(filepath)
    texts = []
    for page in reader.pages[:DEFAULT_MAX_PDF_PAGES]:
        texts.append(page.extract_text() or "")
    return "\n".join(texts)


def _extract_docx_preview(filepath: str) -> str:
    return _extract_docx_text(filepath)[:DEFAULT_PREVIEW_CHARS]


def _extract_docx_text(filepath: str) -> str:
    import docx

    texts = []
    try:
        with zipfile.ZipFile(filepath) as archive:
            root = ET.fromstring(archive.read("word/document.xml"))
            for node in root.iter():
                if node.tag.endswith("}t") and node.text:
                    texts.append(node.text.strip())
    except Exception:
        document = docx.Document(filepath)
        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            if text:
                texts.append(text)
    return "\n".join(texts)


def _extract_pptx_preview(filepath: str) -> str:
    texts = []
    with zipfile.ZipFile(filepath) as archive:
        slide_names = sorted(
            name
            for name in archive.namelist()
            if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        )
        for slide_name in slide_names:
            root = ET.fromstring(archive.read(slide_name))
            for node in root.iter():
                if node.tag.endswith("}t") and node.text:
                    texts.append(node.text.strip())
            if len("\n".join(texts)) >= DEFAULT_PREVIEW_CHARS:
                break
    return "\n".join(text for text in texts if text)


def _normalize_preview(text: str) -> str:
    preview = "\n".join(line.strip() for line in (text or "").splitlines())
    preview = "\n".join(line for line in preview.splitlines() if line)
    return preview[:DEFAULT_PREVIEW_CHARS].strip()


def _normalize_extracted_text(text: str) -> str:
    extracted_text = "\n".join(line.strip() for line in (text or "").splitlines())
    extracted_text = "\n".join(line for line in extracted_text.splitlines() if line)
    return extracted_text[:DEFAULT_SEARCH_TEXT_CHARS].strip()
