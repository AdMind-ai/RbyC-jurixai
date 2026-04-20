# Configuracao basica de logging
import base64
import logging
import os
import tempfile
import urllib.parse
from time import perf_counter
from typing import Optional

import boto3
import requests
from fastmcp import FastMCP
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

try:
    import textract
except ImportError:
    textract = None


def extract_text_from_doc(filepath: str) -> str:
    if not textract:
        return "[ERROR] textract nao instalado."
    try:
        text = textract.process(filepath)
        return text.decode("utf-8", errors="replace")
    except Exception as e:
        logger.error("[DOC ERROR] Falha ao extrair texto do .doc: %s", e, exc_info=True)
        return f"[ERRO] Nao foi possivel extrair texto do arquivo .doc: {e}"


BUCKET_NAME = os.getenv("S3_BUCKET", "rbyc")
DOCUMENT_INDEX_API_URL = os.getenv("DOCUMENT_INDEX_API_URL", "").strip()
DOCUMENT_INDEX_API_KEY = os.getenv("DOCUMENT_INDEX_API_KEY", "").strip()
MCP_CUSTOMER_CODE = os.getenv("MCP_CUSTOMER_CODE", "default").strip()
DOCUMENT_INDEX_TIMEOUT_SECONDS = float(
    os.getenv("DOCUMENT_INDEX_TIMEOUT_SECONDS", "10")
)

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION"),
)

INSTRUCTIONS = """
Servidor MCP para listagem e leitura de documentos armazenados no S3.
Ferramentas disponiveis:
- list_documents: lista arquivos no bucket com filtros opcionais para reduzir o universo de busca
- get_document: retorna um trecho do conteudo do arquivo por padrao. Use mode='full' apenas quando precisar de leitura completa. Use mode='ocr' somente como ultima alternativa para PDFs indispensaveis sem texto nativo.
"""

mcp = FastMCP(name=BUCKET_NAME, instructions=INSTRUCTIONS)


def _matches_document_filters(
    key: str,
    query: str = "",
    year: str = "",
    extension: str = "",
    filename_contains: str = "",
    path_contains: str = "",
) -> bool:
    key_lower = key.lower()
    query_lower = query.strip().lower()
    year_value = year.strip()
    extension_value = extension.strip().lower()
    filename_contains_value = filename_contains.strip().lower()
    path_contains_value = path_contains.strip().lower()

    if year_value and year_value not in key:
        return False

    if extension_value:
        normalized_extension = (
            extension_value
            if extension_value.startswith(".")
            else f".{extension_value}"
        )
        if not key_lower.endswith(normalized_extension):
            return False

    if filename_contains_value and filename_contains_value not in key_lower:
        return False

    if path_contains_value and path_contains_value not in key_lower:
        return False

    if query_lower:
        query_terms = [term for term in query_lower.split() if term]
        if query_terms and not all(term in key_lower for term in query_terms):
            return False

    return True


def _serialize_document_metadata(obj: dict) -> dict:
    key = obj["Key"]
    filename = key.split("/")[-1]
    extension = os.path.splitext(filename)[1].lower()
    last_modified = obj.get("LastModified")
    return {
        "key": key,
        "filename": filename,
        "extension": extension,
        "size_bytes": obj.get("Size", 0),
        "last_modified": last_modified.isoformat() if last_modified else None,
        "path": key,
    }


def _list_documents_from_index(
    query: str = "",
    year: str = "",
    extension: str = "",
    filename_contains: str = "",
    path_contains: str = "",
    limit: int = 200,
    sort_by: str = "last_modified",
    sort_order: str = "desc",
) -> Optional[list]:
    if not DOCUMENT_INDEX_API_URL or not DOCUMENT_INDEX_API_KEY:
        return None

    params = {
        "customer_code": MCP_CUSTOMER_CODE,
        "query": query,
        "year": year,
        "extension": extension,
        "filename_contains": filename_contains,
        "path_contains": path_contains,
        "limit": str(limit),
        "sort_by": sort_by,
        "sort_order": sort_order,
    }
    url = f"{DOCUMENT_INDEX_API_URL}?{urllib.parse.urlencode(params)}"
    parsed_url = urllib.parse.urlparse(DOCUMENT_INDEX_API_URL)
    request_started_at = perf_counter()
    logger.info(
        "[mcp_ricerca] document_index_request host=%s path=%s customer_code=%s timeout_seconds=%s",
        parsed_url.netloc or "<empty>",
        parsed_url.path or "<empty>",
        MCP_CUSTOMER_CODE or "<empty>",
        DOCUMENT_INDEX_TIMEOUT_SECONDS,
    )
    try:
        response = requests.get(
            url,
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "identity",
                "Connection": "close",
                "User-Agent": "rbyc-mcp-document-index/1.0",
                "X-Internal-API-Key": DOCUMENT_INDEX_API_KEY,
            },
            timeout=DOCUMENT_INDEX_TIMEOUT_SECONDS,
        )
        duration_ms = round((perf_counter() - request_started_at) * 1000, 2)
        if response.status_code != 200:
            logger.warning(
                "[mcp_ricerca] document_index_unavailable status=%s duration_ms=%s response_length=%s",
                response.status_code,
                duration_ms,
                len(response.content),
            )
            return None

        documents = response.json()
        logger.info(
            "[mcp_ricerca] document_index_response status=%s duration_ms=%s returned_documents=%s response_length=%s",
            response.status_code,
            duration_ms,
            len(documents) if isinstance(documents, list) else "<unknown>",
            len(response.content),
        )
        return documents
    except (requests.RequestException, ValueError) as exc:
        duration_ms = round((perf_counter() - request_started_at) * 1000, 2)
        logger.warning(
            "[mcp_ricerca] document_index_unavailable error=%s duration_ms=%s host=%s path=%s",
            exc,
            duration_ms,
            parsed_url.netloc or "<empty>",
            parsed_url.path or "<empty>",
        )
        return None


@mcp.tool()
async def list_documents(
    query: str = "",
    year: str = "",
    extension: str = "",
    filename_contains: str = "",
    path_contains: str = "",
    limit: int = 200,
    sort_by: str = "last_modified",
    sort_order: str = "desc",
) -> list:
    """Lista arquivos do bucket com filtros, ordenacao e metadados para descoberta rapida."""
    started_at = perf_counter()
    limit = max(1, min(limit, 300))
    sort_by = (sort_by or "last_modified").strip().lower()
    sort_order = (sort_order or "desc").strip().lower()
    if sort_by not in {"last_modified", "size", "filename"}:
        sort_by = "last_modified"
    if sort_order not in {"asc", "desc"}:
        sort_order = "desc"

    indexed_documents = _list_documents_from_index(
        query=query,
        year=year,
        extension=extension,
        filename_contains=filename_contains,
        path_contains=path_contains,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    if indexed_documents is not None:
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        logger.info(
            "[mcp_ricerca] list_documents completed source=index duration_ms=%s returned_documents=%s limit=%s sort_by=%s sort_order=%s query=%s year=%s extension=%s filename_contains=%s path_contains=%s customer_code=%s",
            duration_ms,
            len(indexed_documents),
            limit,
            sort_by,
            sort_order,
            query or "<empty>",
            year or "<empty>",
            extension or "<empty>",
            filename_contains or "<empty>",
            path_contains or "<empty>",
            MCP_CUSTOMER_CODE or "<empty>",
        )
        return indexed_documents

    response = s3.list_objects_v2(Bucket=BUCKET_NAME)
    contents = response.get("Contents", [])
    filtered_documents = [
        obj
        for obj in contents
        if _matches_document_filters(
            obj["Key"],
            query=query,
            year=year,
            extension=extension,
            filename_contains=filename_contains,
            path_contains=path_contains,
        )
    ]
    if sort_by == "size":
        sort_key = lambda obj: obj.get("Size") or 0
    elif sort_by == "filename":
        sort_key = lambda obj: obj.get("Key", "").lower()
    else:
        sort_key = lambda obj: obj.get("LastModified") or 0
    filtered_documents.sort(
        key=sort_key,
        reverse=(sort_order == "desc"),
    )
    documents = [
        _serialize_document_metadata(obj) for obj in filtered_documents[:limit]
    ]
    duration_ms = round((perf_counter() - started_at) * 1000, 2)
    logger.info(
        "[mcp_ricerca] list_documents completed source=s3 duration_ms=%s total_documents=%s filtered_documents=%s returned_documents=%s limit=%s sort_by=%s sort_order=%s query=%s year=%s extension=%s filename_contains=%s path_contains=%s",
        duration_ms,
        len(contents),
        len(filtered_documents),
        len(documents),
        limit,
        sort_by,
        sort_order,
        query or "<empty>",
        year or "<empty>",
        extension or "<empty>",
        filename_contains or "<empty>",
        path_contains or "<empty>",
    )
    return documents


try:
    import pypdf
except ImportError:
    pypdf = None
try:
    import docx
except ImportError:
    docx = None
try:
    import pandas as pd
except ImportError:
    pd = None
try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None
try:
    import pytesseract
except ImportError:
    pytesseract = None


def extract_text_from_pdf(filepath: str, use_ocr: bool = False) -> str:
    if not pypdf:
        return "[ERROR] pypdf nao instalado."

    started_at = perf_counter()
    used_ocr = False

    try:
        reader = pypdf.PdfReader(filepath)
        texts = []
        for i, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text() or ""
                texts.append(page_text)
            except Exception as e:
                logger.error(
                    "[PDF ERROR] Falha ao extrair texto da pagina %s: %s",
                    i + 1,
                    e,
                    exc_info=True,
                )
                texts.append(f"[ERRO ao extrair texto da pagina {i + 1}]")

        result = "\n".join(texts)
        if not result.strip() and use_ocr and convert_from_path and pytesseract:
            used_ocr = True
            try:
                images = convert_from_path(filepath)
                ocr_texts = []
                for img in images:
                    ocr_text = pytesseract.image_to_string(img, lang="por+eng+ita")
                    ocr_texts.append(ocr_text)
                ocr_result = "\n".join(ocr_texts)
                duration_ms = round((perf_counter() - started_at) * 1000, 2)
                logger.info(
                    "[mcp_ricerca] extract_text_from_pdf completed duration_ms=%s pages=%s used_ocr=%s extracted_chars=%s",
                    duration_ms,
                    len(reader.pages),
                    used_ocr,
                    len(ocr_result),
                )
                if ocr_result.strip():
                    return ocr_result
                return "[ERRO] Nao foi possivel extrair texto deste PDF nem via OCR."
            except Exception as ocr_e:
                logger.error("[PDF OCR ERROR] %s", ocr_e, exc_info=True)
                return f"[ERRO] Nao foi possivel extrair texto nem via OCR: {ocr_e}"

        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        logger.info(
            "[mcp_ricerca] extract_text_from_pdf completed duration_ms=%s pages=%s used_ocr=%s extracted_chars=%s",
            duration_ms,
            len(reader.pages),
            used_ocr,
            len(result),
        )
        if not result.strip():
            return (
                "[ERRO] Nao foi possivel extrair texto nativo deste PDF no modo rapido. "
                "O documento pode ser escaneado ou conter apenas imagem; use mode='ocr' "
                "apenas se a leitura OCR for realmente necessaria."
            )
        return result
    except Exception as e:
        logger.error("[PDF ERROR] Falha geral ao abrir PDF: %s", e, exc_info=True)
        return f"[ERRO] Nao foi possivel abrir ou ler o PDF: {e}"


def extract_text_from_docx(filepath: str) -> str:
    if not docx:
        return "[ERROR] python-docx nao instalado."
    doc = docx.Document(filepath)
    return "\n".join([p.text for p in doc.paragraphs])


def extract_text_from_xlsx(filepath: str) -> str:
    if not pd:
        return "[ERROR] pandas nao instalado."
    dfs = pd.read_excel(filepath, sheet_name=None)
    text = []
    for sheet, df in dfs.items():
        text.append(f"--- {sheet} ---\n" + df.astype(str).to_string(index=False))
    return "\n\n".join(text)


def _truncate_text(
    content: str,
    max_chars: int,
    metadata_prefix: Optional[str] = None,
) -> str:
    if len(content) <= max_chars:
        return content

    truncated = content[:max_chars].rstrip()
    prefix = f"{metadata_prefix}\n\n" if metadata_prefix else ""
    return (
        f"{prefix}{truncated}\n\n"
        "[TRUNCATED] Conteudo parcial retornado para busca rapida. "
        "Se precisar, solicite o documento completo explicitamente."
    )


@mcp.tool()
async def get_document(
    filename: str,
    mode: str = "excerpt",
    max_chars: int = 12000,
) -> str:
    """
    Baixa o arquivo do S3 e retorna um trecho por padrao.

    Modos:
    - excerpt: modo rapido padrao, sem OCR.
    - full: leitura completa sem OCR.
    - ocr: ultima alternativa para PDFs indispensaveis sem texto nativo.

    Use OCR apenas se o documento for claramente necessario e nao houver fonte alternativa mais leve.
    """
    ext = os.path.splitext(filename)[1].lower()
    started_at = perf_counter()
    mode = (mode or "excerpt").strip().lower()
    if mode not in {"excerpt", "full", "ocr"}:
        mode = "excerpt"
    max_chars = max(1000, min(max_chars, 50000))

    with tempfile.NamedTemporaryFile(delete=True, suffix=ext) as tmp:
        try:
            s3.download_fileobj(BUCKET_NAME, filename, tmp)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            logger.warning(
                "[mcp_ricerca] get_document_not_found filename=%s duration_ms=%s error_code=%s",
                filename,
                duration_ms,
                error_code or "<unknown>",
            )
            return (
                f"[ERRO] Documento nao encontrado ou indisponivel: {filename}. "
                "Tente listar novamente os documentos antes de abrir este arquivo."
            )

        tmp.flush()
        file_size_bytes = tmp.tell()

        try:
            if ext in [".txt", ".md", ".csv"]:
                tmp.seek(0)
                content = tmp.read().decode("utf-8", errors="replace")
            elif ext == ".pdf":
                content = extract_text_from_pdf(tmp.name, use_ocr=(mode == "ocr"))
            elif ext == ".docx":
                content = extract_text_from_docx(tmp.name)
            elif ext == ".doc":
                content = extract_text_from_doc(tmp.name)
            elif ext == ".xlsx":
                content = extract_text_from_xlsx(tmp.name)
            else:
                tmp.seek(0)
                content = base64.b64encode(tmp.read()).decode("utf-8")

            returned_content = content
            if mode != "full" and ext not in {".txt", ".md", ".csv"}:
                metadata_prefix = (
                    f"filename={filename}\n"
                    f"mode={mode}\n"
                    f"file_extension={ext or '<none>'}\n"
                    f"file_size_bytes={file_size_bytes}"
                )
                returned_content = _truncate_text(
                    content,
                    max_chars=max_chars,
                    metadata_prefix=metadata_prefix,
                )

            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            logger.info(
                "[mcp_ricerca] get_document completed filename=%s ext=%s mode=%s duration_ms=%s file_size_bytes=%s extracted_chars=%s returned_chars=%s",
                filename,
                ext or "<none>",
                mode,
                duration_ms,
                file_size_bytes,
                len(content),
                len(returned_content),
            )
            return returned_content
        except Exception as e:
            logger.error(
                "[ERROR] Falha ao processar arquivo %s: %s",
                filename,
                e,
                exc_info=True,
            )
            return f"[ERRO] Nao foi possivel processar o arquivo: {e}"


if __name__ == "__main__":
    logger.info("Servidor MCP iniciado em http://localhost:7000/mcp")
    mcp.run(host="0.0.0.0", port=7000, transport="sse")
