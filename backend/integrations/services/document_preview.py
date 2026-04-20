import logging
import os
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass

from django.utils import timezone

from core.utils.s3_utils import _get_s3_client
from integrations.models import DocumentIndex


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


def build_missing_document_previews(
    customer_code: str = "",
    filename_contains: str = "",
    path_contains: str = "",
    document_type: str = "",
    year: str = "",
    limit: int = 100,
    force: bool = False,
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

    documents = documents.order_by("-last_modified", "id")[: max(1, limit)]
    s3_client = _get_s3_client()
    result = DocumentPreviewResult()

    for document in documents:
        try:
            preview = extract_document_preview(document, s3_client=s3_client)
            if preview:
                document.text_preview = preview
                document.extraction_status = DocumentIndex.STATUS_READY
                document.extraction_error = ""
                result.processed_count += 1
            else:
                document.extraction_status = DocumentIndex.STATUS_SKIPPED
                document.extraction_error = "Preview not supported or empty."
                result.skipped_count += 1

            document.indexed_at = timezone.now()
            document.save(
                update_fields=[
                    "text_preview",
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


def extract_document_preview(document: DocumentIndex, s3_client=None) -> str:
    if document.size_bytes > DEFAULT_MAX_FILE_BYTES:
        return ""

    extension = (document.extension or "").lower()
    if extension not in {".pdf", ".docx", ".pptx", ".txt", ".md", ".csv"}:
        return ""

    s3_client = s3_client or _get_s3_client()
    suffix = extension or ".tmp"
    with tempfile.NamedTemporaryFile(delete=True, suffix=suffix) as tmp:
        s3_client.download_fileobj(document.bucket_name, document.object_key, tmp)
        tmp.flush()

        if extension == ".pdf":
            preview = _extract_pdf_preview(tmp.name)
        elif extension == ".docx":
            preview = _extract_docx_preview(tmp.name)
        elif extension == ".pptx":
            preview = _extract_pptx_preview(tmp.name)
        else:
            tmp.seek(0)
            preview = tmp.read(DEFAULT_PREVIEW_CHARS * 2).decode(
                "utf-8",
                errors="replace",
            )

    return _normalize_preview(preview)


def _extract_pdf_preview(filepath: str) -> str:
    from PyPDF2 import PdfReader

    reader = PdfReader(filepath)
    texts = []
    for page in reader.pages[:DEFAULT_MAX_PDF_PAGES]:
        texts.append(page.extract_text() or "")
    return "\n".join(texts)


def _extract_docx_preview(filepath: str) -> str:
    import docx

    document = docx.Document(filepath)
    texts = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if text:
            texts.append(text)
        if len("\n".join(texts)) >= DEFAULT_PREVIEW_CHARS:
            break
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
