# Configuracao basica de logging
import base64
import logging
import os
import re
import tempfile
import unicodedata
import urllib.parse
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from time import perf_counter
from typing import Optional

import boto3
import jwt
import requests
from fastmcp import FastMCP
from fastmcp import Context
from fastmcp.server.dependencies import get_http_request
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

QUERY_SYNONYMS = {
    "rso": [
        "relazione sulla struttura organizzativa",
        "struttura organizzativa",
    ],
    "relazione sulla struttura organizzativa": ["rso", "struttura organizzativa"],
    "struttura organizzativa": ["rso", "relazione sulla struttura organizzativa"],
}

RECENCY_QUERY_MARKERS = (
    "ultima",
    "ultimo",
    "ultim",
    "piu recente",
    "recent",
    "approvat",
    "approvazione",
)

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
DOCUMENT_INDEX_CONTENT_API_URL = os.getenv(
    "DOCUMENT_INDEX_CONTENT_API_URL",
    "",
).strip()
DOCUMENT_INDEX_API_KEY = os.getenv("DOCUMENT_INDEX_API_KEY", "").strip()
MCP_CUSTOMER_CODE = os.getenv("MCP_CUSTOMER_CODE", "default").strip()
MCP_INTERNAL_AUTH_SECRET = (
    os.getenv("MCP_INTERNAL_AUTH_SECRET", "").strip()
    or DOCUMENT_INDEX_API_KEY
)
MCP_INTERNAL_AUTH_ISSUER = os.getenv(
    "MCP_INTERNAL_AUTH_ISSUER",
    "backend-integrations",
).strip()
MCP_INTERNAL_AUTH_AUDIENCE = os.getenv(
    "MCP_INTERNAL_AUTH_AUDIENCE",
    "mcp-ricerca",
).strip()
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
- search_documents: busca documentos relevantes no indice e retorna metadados com preview curto. Use primeiro para perguntas amplas, exploratorias ou tematicas.
- list_documents: lista arquivos no bucket com filtros opcionais para reduzir o universo de busca
- get_document: retorna um trecho do conteudo do arquivo por padrao. Use mode='full' apenas quando precisar de leitura completa. Use mode='ocr' somente como ultima alternativa para PDFs indispensaveis sem texto nativo.
"""

mcp = FastMCP(name=BUCKET_NAME, instructions=INSTRUCTIONS)


class MCPAuthError(RuntimeError):
    pass


@dataclass(frozen=True)
class MCPClientContext:
    client_id: Optional[int]
    customer_code: str
    bucket_name: str
    access_token: Optional[str] = None
    source: str = "fallback"


_active_client_context: ContextVar[Optional[MCPClientContext]] = ContextVar(
    "mcp_active_client_context",
    default=None,
)


def _default_client_context() -> MCPClientContext:
    return MCPClientContext(
        client_id=None,
        customer_code=MCP_CUSTOMER_CODE,
        bucket_name=BUCKET_NAME,
        access_token=None,
        source="fallback",
    )


def _decode_mcp_access_token(token: str) -> MCPClientContext:
    if not MCP_INTERNAL_AUTH_SECRET:
        raise MCPAuthError("MCP internal auth secret is not configured.")

    try:
        payload = jwt.decode(
            token,
            MCP_INTERNAL_AUTH_SECRET,
            algorithms=["HS256"],
            audience=MCP_INTERNAL_AUTH_AUDIENCE,
            issuer=MCP_INTERNAL_AUTH_ISSUER,
        )
    except jwt.PyJWTError as exc:
        raise MCPAuthError("Invalid MCP authentication token.") from exc

    customer_code = str(payload.get("customer_code") or "").strip()
    bucket_name = str(payload.get("bucket_name") or "").strip()
    client_id = payload.get("client_id")
    if not customer_code or not bucket_name:
        raise MCPAuthError("MCP authentication token is missing required claims.")

    try:
        normalized_client_id = int(client_id) if client_id is not None else None
    except (TypeError, ValueError) as exc:
        raise MCPAuthError("MCP authentication token has an invalid client_id.") from exc

    return MCPClientContext(
        client_id=normalized_client_id,
        customer_code=customer_code,
        bucket_name=bucket_name,
        access_token=token,
        source="token",
    )


def _extract_mcp_access_token() -> Optional[str]:
    try:
        request = get_http_request()
    except RuntimeError:
        return None

    authorization = request.headers.get("authorization", "").strip()
    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        if token:
            return token

    query_token = request.query_params.get("mcp_token", "").strip()
    return query_token or None


def _resolve_client_context() -> MCPClientContext:
    token = _extract_mcp_access_token()
    if not token:
        return _default_client_context()
    return _decode_mcp_access_token(token)


def _activate_client_context(ctx: Context) -> object:
    client_context = _resolve_client_context()
    ctx.set_state("client_context", client_context)
    return _active_client_context.set(client_context)


def _get_active_client_context() -> MCPClientContext:
    client_context = _active_client_context.get()
    if client_context is not None:
        return client_context
    return _default_client_context()


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


def _infer_document_date_from_key(object_key: str) -> Optional[str]:
    value = object_key or ""
    date_patterns = (
        (lambda groups: f"{groups[0]}{groups[1]}{groups[2]}", "%d%m%Y", r"(?<!\d)(\d{2})(\d{2})(20\d{2})(?!\d)"),
        (lambda groups: f"{groups[0]}-{groups[1]}-{groups[2]}", "%d-%m-%Y", r"(?<!\d)(\d{2})[-_./](\d{2})[-_./](20\d{2})(?!\d)"),
        (lambda groups: f"{groups[0]}{groups[1]}{groups[2]}", "%Y%m%d", r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)"),
    )

    for builder, date_format, pattern in date_patterns:
        match = re.search(pattern, value, flags=re.IGNORECASE)
        if not match:
            continue
        try:
            return datetime.strptime(builder(match.groups()), date_format).date().isoformat()
        except ValueError:
            continue

    return None


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
        "s3_last_modified": last_modified.isoformat() if last_modified else None,
        "last_modified": last_modified.isoformat() if last_modified else None,
        "document_date": _infer_document_date_from_key(key),
        "path": key,
    }


def _list_documents_from_s3(
    *,
    query: str = "",
    year: str = "",
    extension: str = "",
    filename_contains: str = "",
    path_contains: str = "",
    limit: int = 200,
    sort_by: str = "last_modified",
    sort_order: str = "desc",
) -> list[dict]:
    client_context = _get_active_client_context()
    paginator = s3.get_paginator("list_objects_v2")
    contents = []
    for page in paginator.paginate(Bucket=client_context.bucket_name):
        contents.extend(page.get("Contents", []))
    filtered_documents = [
        _serialize_document_metadata(obj)
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
        sort_key = lambda obj: obj.get("size_bytes") or 0
    elif sort_by == "filename":
        sort_key = lambda obj: obj.get("filename", "").lower()
    elif sort_by == "document_date":
        sort_key = lambda obj: obj.get("document_date") or ""
    elif sort_by == "s3_last_modified":
        sort_key = lambda obj: obj.get("s3_last_modified") or ""
    else:
        sort_key = lambda obj: obj.get("s3_last_modified") or obj.get("last_modified") or ""
    filtered_documents.sort(
        key=sort_key,
        reverse=(sort_order == "desc"),
    )
    return filtered_documents[:limit]


def _list_documents_from_index(
    query: str = "",
    year: str = "",
    document_type: str = "",
    document_family: str = "",
    control_function_tags: str = "",
    topic_tags: str = "",
    extension: str = "",
    filename_contains: str = "",
    path_contains: str = "",
    limit: int = 200,
    sort_by: str = "last_modified",
    sort_order: str = "desc",
) -> Optional[list]:
    if not DOCUMENT_INDEX_API_URL or not DOCUMENT_INDEX_API_KEY:
        return None

    client_context = _get_active_client_context()

    params = {
        "customer_code": client_context.customer_code,
        "query": query,
        "year": year,
        "document_type": document_type,
        "document_family": document_family,
        "control_function_tags": control_function_tags,
        "topic_tags": topic_tags,
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
        client_context.customer_code or "<empty>",
        DOCUMENT_INDEX_TIMEOUT_SECONDS,
    )
    try:
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "Connection": "close",
            "User-Agent": "rbyc-mcp-document-index/1.0",
            "X-Internal-API-Key": DOCUMENT_INDEX_API_KEY,
        }
        if client_context.access_token:
            headers["Authorization"] = f"Bearer {client_context.access_token}"

        response = requests.get(
            url,
            headers=headers,
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


def _document_index_content_url() -> str:
    if DOCUMENT_INDEX_CONTENT_API_URL:
        return DOCUMENT_INDEX_CONTENT_API_URL
    if DOCUMENT_INDEX_API_URL.endswith("/internal/document-index/"):
        return DOCUMENT_INDEX_API_URL.replace(
            "/internal/document-index/",
            "/internal/document-index-content/",
        )
    return ""


def _persist_document_content_to_index(
    *,
    document_key: str,
    text_preview: str,
    extracted_text: str,
) -> None:
    content_url = _document_index_content_url()
    if not content_url or not DOCUMENT_INDEX_API_KEY:
        return

    client_context = _get_active_client_context()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "rbyc-mcp-document-index/1.0",
        "X-Internal-API-Key": DOCUMENT_INDEX_API_KEY,
    }
    if client_context.access_token:
        headers["Authorization"] = f"Bearer {client_context.access_token}"

    payload = {
        "key": document_key,
        "text_preview": (text_preview or "")[:6000],
        "extracted_text": (extracted_text or "")[:30000],
    }
    try:
        response = requests.post(
            content_url,
            headers=headers,
            json=payload,
            timeout=DOCUMENT_INDEX_TIMEOUT_SECONDS,
        )
        if response.status_code >= 400:
            logger.warning(
                "[mcp_ricerca] document_index_content_update_failed status=%s key=%s response_length=%s",
                response.status_code,
                document_key,
                len(response.content),
            )
        else:
            logger.info(
                "[mcp_ricerca] document_index_content_update_completed key=%s preview_chars=%s extracted_chars=%s",
                document_key,
                len(payload["text_preview"]),
                len(payload["extracted_text"]),
            )
    except requests.RequestException as exc:
        logger.warning(
            "[mcp_ricerca] document_index_content_update_failed error=%s key=%s",
            exc,
            document_key,
        )


def _normalize_search_value(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    normalized = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return " ".join(normalized.casefold().split())


def _query_terms(query: str) -> list[str]:
    normalized = _normalize_search_value(query)
    return [term for term in normalized.split() if len(term) > 2][:8]


def _expanded_query_terms(query: str) -> list[str]:
    normalized = _normalize_search_value(query)
    expanded_terms = []

    for term in _query_terms(query):
        if term not in expanded_terms:
            expanded_terms.append(term)

    for source, synonyms in QUERY_SYNONYMS.items():
        if source in normalized:
            if source not in expanded_terms:
                expanded_terms.append(source)
            for synonym in synonyms:
                normalized_synonym = _normalize_search_value(synonym)
                if normalized_synonym and normalized_synonym not in expanded_terms:
                    expanded_terms.append(normalized_synonym)

    return expanded_terms[:12]


def _query_requires_recency(query: str) -> bool:
    normalized = _normalize_search_value(query)
    return any(marker in normalized for marker in RECENCY_QUERY_MARKERS)


def _query_requires_approval_evidence(query: str) -> bool:
    normalized = _normalize_search_value(query)
    return any(
        marker in normalized
        for marker in ("approvat", "approvazione", "deliberat", "delibera")
    )


def _is_searchable_document(document: dict) -> bool:
    filename = (document.get("filename") or "").strip()
    key = (document.get("key") or document.get("path") or "").strip()
    if not filename or key.endswith("/"):
        return False
    return True


def _score_search_document(document: dict, query: str) -> int:
    terms = _expanded_query_terms(query)
    if not terms:
        return 0

    filename = _normalize_search_value(document.get("filename") or "")
    key = _normalize_search_value(document.get("key") or document.get("path") or "")
    document_type = _normalize_search_value(document.get("document_type") or "")
    document_family = _normalize_search_value(
        document.get("document_family") or ""
    )
    control_function_tags = _normalize_search_value(
        document.get("control_function_tags") or ""
    )
    topic_tags = _normalize_search_value(document.get("topic_tags") or "")
    preview = _normalize_search_value(document.get("text_preview") or "")

    score = 0
    for term in terms:
        if term in filename:
            score += 6
        if term in document_type:
            score += 4
        if document_family and term in document_family:
            score += 5
        if control_function_tags and term in control_function_tags:
            score += 5
        if topic_tags and term in topic_tags:
            score += 5
        if term in key:
            score += 3
        if preview and term in preview:
            score += 2

    if document.get("text_preview"):
        score += 1
    return score


def _compact_preview(document: dict, max_chars: int) -> str:
    preview = " ".join((document.get("text_preview") or "").split())
    if len(preview) <= max_chars:
        return preview
    return f"{preview[:max_chars].rstrip()}..."


def _document_search_queries(query: str) -> list[str]:
    cleaned = " ".join((query or "").strip().split())
    normalized = _normalize_search_value(cleaned)
    queries = []
    for candidate in [cleaned, normalized]:
        if candidate and candidate not in queries:
            queries.append(candidate)

    for source, synonyms in QUERY_SYNONYMS.items():
        if source in normalized:
            if source not in queries:
                queries.append(source)
            for synonym in synonyms:
                normalized_synonym = _normalize_search_value(synonym)
                if synonym and synonym not in queries:
                    queries.append(synonym)
                if normalized_synonym and normalized_synonym not in queries:
                    queries.append(normalized_synonym)

    terms = _query_terms(cleaned)
    if terms:
        # Keep the fallback space narrow: prefer the strongest lexical anchor only.
        longest_term = max(terms, key=len)
        if longest_term not in queries:
            queries.append(longest_term)
    return queries[:3] or [""]


def _dedupe_documents(documents: list[dict]) -> list[dict]:
    seen_keys = set()
    deduped = []
    for document in documents:
        key = document.get("key") or document.get("path") or document.get("filename")
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(document)
    return deduped


def _score_s3_search_document(document: dict, query: str) -> int:
    terms = _expanded_query_terms(query)
    if not terms:
        return 0

    filename = _normalize_search_value(document.get("filename") or "")
    key = _normalize_search_value(document.get("key") or document.get("path") or "")
    score = 0
    for term in terms:
        if term in filename:
            score += 6
        if term in key:
            score += 3
    return score


def _score_index_search_document(document: dict, query: str) -> int:
    backend_score = 0
    try:
        backend_score = int(document.get("relevance_score") or 0)
    except (TypeError, ValueError):
        backend_score = 0

    lexical_score = _score_search_document(document, query)
    if backend_score <= 0:
        return lexical_score

    # The backend index already applies richer FTS + metadata/artifact-aware ranking.
    # In index/hybrid mode, preserve that ordering signal and only let local lexical
    # scoring provide a small tie-break/boost instead of re-ranking from scratch.
    return backend_score + min(lexical_score, 12)


def _document_relevance_score(document: dict, query: str, *, source: str) -> int:
    if source == "s3":
        return _score_s3_search_document(document, query)
    if source == "hybrid":
        return max(
            _score_index_search_document(document, query),
            _score_s3_search_document(document, query),
        )
    if source == "index":
        return _score_index_search_document(document, query)
    return _score_search_document(document, query)


def _document_recency_value(document: dict) -> tuple[str, str]:
    return (
        str(document.get("document_date") or ""),
        str(
            document.get("s3_last_modified")
            or document.get("last_modified")
            or ""
        ),
    )


def _sort_documents_by_score_and_recency(documents: list[dict], query: str, *, source: str) -> list[dict]:
    if not documents:
        return []

    recency_sensitive_query = _query_requires_recency(query)

    def sort_key(document: dict) -> tuple[object, object, str, str]:
        score = _document_relevance_score(document, query, source=source)
        document_date, s3_last_modified = _document_recency_value(document)
        return (
            document_date if recency_sensitive_query else score,
            score if recency_sensitive_query else document_date,
            s3_last_modified,
        )

    return sorted(documents, key=sort_key, reverse=True)


def _document_ranking_debug(document: dict, query: str, *, source: str) -> dict:
    return {
        "filename": document.get("filename") or "",
        "key": document.get("key") or document.get("path") or "",
        "relevance_score": _document_relevance_score(document, query, source=source),
        "document_date": document.get("document_date") or "",
        "s3_last_modified": (
            document.get("s3_last_modified")
            or document.get("last_modified")
            or ""
        ),
        "source": source,
    }


def _read_cost_tier(
    *,
    mode: str,
    ext: str,
    file_size_bytes: int = 0,
    source: str = "download",
) -> str:
    if source == "preview":
        return "light"

    if mode == "ocr":
        return "heavy"

    if mode == "full":
        if ext == ".pdf" or file_size_bytes >= 1_000_000:
            return "heavy"
        return "medium"

    if ext == ".pdf" or file_size_bytes >= 1_000_000:
        return "medium"

    return "light"


@mcp.tool()
async def search_documents(
    query: str,
    year: str = "",
    document_type: str = "",
    document_family: str = "",
    control_function_tags: str = "",
    topic_tags: str = "",
    extension: str = "",
    limit: int = 5,
    preview_chars: int = 1200,
    ctx: Context = None,
) -> list:
    """
    Busca documentos relevantes usando o indice e retorna metadados com preview.

    Use esta ferramenta antes de get_document para perguntas amplas, exploratorias
    ou tematicas. Ela reduz leituras completas e evita OCR desnecessario.
    """
    reset_token = _activate_client_context(ctx)
    started_at = perf_counter()
    try:
        client_context = _get_active_client_context()
        limit = max(1, min(limit, 20))
        preview_chars = max(300, min(preview_chars, 3000))
        candidate_limit = max(20, min(limit * 8, 100))
        enough_candidate_count = max(3, min(limit, 5))
        recency_sensitive_query = _query_requires_recency(query)
        approval_sensitive_query = _query_requires_approval_evidence(query)
        strong_structured_filters = any(
            (
                (year or "").strip(),
                (document_type or "").strip(),
                (document_family or "").strip(),
                (control_function_tags or "").strip(),
                (topic_tags or "").strip(),
            )
        )

        candidate_documents = []
        index_unavailable = False
        for attempt_index, search_query in enumerate(
            _document_search_queries(query),
            start=1,
        ):
            documents = _list_documents_from_index(
                query=search_query,
                year=year,
                document_type=document_type,
                document_family=document_family,
                control_function_tags=control_function_tags,
                topic_tags=topic_tags,
                extension=extension,
                limit=candidate_limit,
                sort_by="last_modified",
                sort_order="desc",
            )
            if documents is None:
                index_unavailable = True
                break
            candidate_documents.extend(documents)
            unique_count = len(_dedupe_documents(candidate_documents))
            if unique_count >= enough_candidate_count:
                break
            if unique_count >= candidate_limit:
                break
            if strong_structured_filters and unique_count == 0 and attempt_index >= 2:
                break

        used_source = "index"
        unique_documents = []
        ranked_documents = []
        if candidate_documents:
            unique_documents = [
                document
                for document in _dedupe_documents(candidate_documents)
                if _is_searchable_document(document)
            ]
            if recency_sensitive_query:
                s3_documents = []
                for search_query in _document_search_queries(query):
                    documents = _list_documents_from_s3(
                        query=search_query,
                        year=year,
                        extension=extension,
                        limit=candidate_limit,
                        sort_by="last_modified",
                        sort_order="desc",
                    )
                    s3_documents.extend(documents)
                    if len(_dedupe_documents(s3_documents)) >= candidate_limit:
                        break

                if s3_documents:
                    used_source = "hybrid"
                    unique_documents = [
                        document
                        for document in _dedupe_documents(
                            unique_documents + s3_documents
                        )
                        if _is_searchable_document(document)
                    ]

            ranked_documents = _sort_documents_by_score_and_recency(
                unique_documents,
                query,
                source=used_source,
            )
        else:
            used_source = "s3_fallback"
            s3_documents = []
            for search_query in _document_search_queries(query):
                documents = _list_documents_from_s3(
                    query=search_query,
                    year=year,
                    extension=extension,
                    limit=candidate_limit,
                    sort_by="last_modified",
                    sort_order="desc",
                )
                s3_documents.extend(documents)
                if len(_dedupe_documents(s3_documents)) >= candidate_limit:
                    break

            unique_documents = [
                document
                for document in _dedupe_documents(s3_documents)
                if _is_searchable_document(document)
            ]
            ranked_documents = _sort_documents_by_score_and_recency(
                unique_documents,
                query,
                source="s3",
            )

        results = []
        for document in ranked_documents[:limit]:
            results.append(
                {
                    "key": document.get("key") or document.get("path") or "",
                    "filename": document.get("filename") or "",
                    "extension": document.get("extension") or "",
                    "year": document.get("year") or "",
                    "document_type": document.get("document_type") or "",
                    "document_family": document.get("document_family") or "",
                    "control_function_tags": (
                        document.get("control_function_tags") or ""
                    ),
                    "topic_tags": document.get("topic_tags") or "",
                    "document_date": document.get("document_date"),
                    "s3_last_modified": (
                        document.get("s3_last_modified")
                        or document.get("last_modified")
                    ),
                    "last_modified": document.get("last_modified"),
                    "size_bytes": document.get("size_bytes") or 0,
                    "preview": _compact_preview(document, preview_chars),
                    "relevance_score": _document_relevance_score(
                        document,
                        query,
                        source=used_source,
                    ),
                }
            )

        top_result = results[0] if results else None
        if top_result:
            ranking_debug = _document_ranking_debug(
                top_result,
                query,
                source=used_source,
            )
            logger.info(
                "[mcp_ricerca] ranking_top_result query=%s filename=%s key=%s relevance_score=%s document_date=%s s3_last_modified=%s source=%s",
                query or "<empty>",
                ranking_debug["filename"] or "<empty>",
                ranking_debug["key"] or "<empty>",
                ranking_debug["relevance_score"],
                ranking_debug["document_date"] or "<empty>",
                ranking_debug["s3_last_modified"] or "<empty>",
                ranking_debug["source"],
            )
            if approval_sensitive_query:
                logger.info(
                    "[mcp_ricerca] approval_evidence_requires_document_content query=%s filename=%s document_date=%s s3_last_modified=%s",
                    query or "<empty>",
                    top_result.get("filename") or "<empty>",
                    top_result.get("document_date") or "<empty>",
                    top_result.get("s3_last_modified")
                    or top_result.get("last_modified")
                    or "<empty>",
                )

        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        logger.info(
            "[mcp_ricerca] search_documents completed duration_ms=%s returned_documents=%s candidates=%s source=%s index_unavailable=%s query=%s year=%s document_type=%s document_family=%s control_function_tags=%s topic_tags=%s extension=%s customer_code=%s bucket_name=%s context_source=%s",
            duration_ms,
            len(results),
            len(unique_documents),
            used_source,
            index_unavailable,
            query or "<empty>",
            year or "<empty>",
            document_type or "<empty>",
            document_family or "<empty>",
            control_function_tags or "<empty>",
            topic_tags or "<empty>",
            extension or "<empty>",
            client_context.customer_code or "<empty>",
            client_context.bucket_name or "<empty>",
            client_context.source,
        )
        return results
    finally:
        _active_client_context.reset(reset_token)


def _resolve_document_from_index(filename: str) -> Optional[dict]:
    requested_filename = (filename or "").strip()
    if not requested_filename or "/" in requested_filename:
        return None

    documents = _list_documents_from_index(
        filename_contains=requested_filename,
        limit=10,
        sort_by="last_modified",
        sort_order="desc",
    )
    if not documents:
        return None

    requested_lower = requested_filename.lower()
    exact_matches = [
        document
        for document in documents
        if (document.get("filename") or "").lower() == requested_lower
        or (document.get("key") or "").lower().endswith(f"/{requested_lower}")
    ]
    if not exact_matches:
        logger.info(
            "[mcp_ricerca] resolve_document_key skipped filename=%s candidates=%s",
            requested_filename,
            len(documents),
        )
        return None

    resolved_document = _select_accessible_document(exact_matches) or exact_matches[0]
    resolved_key = resolved_document.get("key")
    if resolved_key and resolved_key != requested_filename:
        logger.info(
            "[mcp_ricerca] resolve_document_key completed filename=%s resolved_key=%s candidates=%s",
            requested_filename,
            resolved_key,
            len(exact_matches),
        )
    return resolved_document


def _resolve_document_from_s3(filename: str) -> Optional[dict]:
    requested_filename = (filename or "").strip()
    if not requested_filename:
        return None

    if "/" in requested_filename:
        return {
            "key": requested_filename,
            "path": requested_filename,
            "filename": requested_filename.rsplit("/", 1)[-1],
            "text_preview": "",
        }

    documents = _list_documents_from_s3(
        filename_contains=requested_filename,
        limit=25,
        sort_by="last_modified",
        sort_order="desc",
    )
    if not documents:
        return None

    requested_lower = requested_filename.lower()
    exact_matches = [
        document
        for document in documents
        if (document.get("filename") or "").lower() == requested_lower
        or (document.get("key") or "").lower().endswith(f"/{requested_lower}")
    ]
    if not exact_matches:
        logger.info(
            "[mcp_ricerca] resolve_document_key_from_s3 skipped filename=%s candidates=%s",
            requested_filename,
            len(documents),
        )
        return None

    resolved_document = exact_matches[0]
    logger.info(
        "[mcp_ricerca] resolve_document_key_from_s3 completed filename=%s resolved_key=%s candidates=%s",
        requested_filename,
        resolved_document.get("key") or "<empty>",
        len(exact_matches),
    )
    return resolved_document


def _s3_object_exists(object_key: str) -> bool:
    if not object_key:
        return False

    client_context = _get_active_client_context()
    try:
        s3.head_object(Bucket=client_context.bucket_name, Key=object_key)
        return True
    except ClientError:
        return False


def _select_accessible_document(documents: list[dict]) -> Optional[dict]:
    for document in documents:
        object_key = (document.get("key") or document.get("path") or "").strip()
        if object_key and _s3_object_exists(object_key):
            return document
    return None


def _resolve_document_key_from_index(filename: str) -> Optional[str]:
    document = _resolve_document_from_index(filename)
    return document.get("key") if document else None


def _get_document_preview_from_index(document_key: str) -> Optional[str]:
    if not document_key:
        return None

    documents = _list_documents_from_index(
        path_contains=document_key,
        limit=5,
        sort_by="last_modified",
        sort_order="desc",
    )
    if not documents:
        return None

    exact_matches = [
        document
        for document in documents
        if (document.get("key") or "") == document_key
        or (document.get("path") or "") == document_key
    ]
    if not exact_matches:
        return None

    preview = (exact_matches[0].get("text_preview") or "").strip()
    if preview:
        logger.info(
            "[mcp_ricerca] get_document_preview completed filename=%s preview_chars=%s",
            document_key,
            len(preview),
        )
        return preview
    return None


def _get_document_preview_from_document(document: Optional[dict]) -> Optional[str]:
    if not document:
        return None
    document_key = document.get("key") or document.get("path") or ""
    preview = (document.get("text_preview") or "").strip()
    if preview:
        logger.info(
            "[mcp_ricerca] get_document_preview completed filename=%s preview_chars=%s source=resolved_document",
            document_key,
            len(preview),
        )
        return preview
    return None


@mcp.tool()
async def list_documents(
    ctx: Context,
    query: str = "",
    year: str = "",
    document_family: str = "",
    control_function_tags: str = "",
    topic_tags: str = "",
    extension: str = "",
    filename_contains: str = "",
    path_contains: str = "",
    limit: int = 200,
    sort_by: str = "last_modified",
    sort_order: str = "desc",
) -> list:
    """Lista arquivos do bucket com filtros, ordenacao e metadados para descoberta rapida."""
    reset_token = _activate_client_context(ctx)
    started_at = perf_counter()
    try:
        client_context = _get_active_client_context()
        limit = max(1, min(limit, 300))
        sort_by = (sort_by or "last_modified").strip().lower()
        sort_order = (sort_order or "desc").strip().lower()
        if sort_by not in {"last_modified", "s3_last_modified", "document_date", "size", "filename"}:
            sort_by = "last_modified"
        if sort_order not in {"asc", "desc"}:
            sort_order = "desc"

        indexed_documents = _list_documents_from_index(
            query=query,
            year=year,
            document_family=document_family,
            control_function_tags=control_function_tags,
            topic_tags=topic_tags,
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
                "[mcp_ricerca] list_documents completed source=index duration_ms=%s returned_documents=%s limit=%s sort_by=%s sort_order=%s query=%s year=%s document_family=%s control_function_tags=%s topic_tags=%s extension=%s filename_contains=%s path_contains=%s customer_code=%s bucket_name=%s context_source=%s",
                duration_ms,
                len(indexed_documents),
                limit,
                sort_by,
                sort_order,
                query or "<empty>",
                year or "<empty>",
                document_family or "<empty>",
                control_function_tags or "<empty>",
                topic_tags or "<empty>",
                extension or "<empty>",
                filename_contains or "<empty>",
                path_contains or "<empty>",
                client_context.customer_code or "<empty>",
                client_context.bucket_name or "<empty>",
                client_context.source,
            )
            return indexed_documents

        documents = _list_documents_from_s3(
            query=query,
            year=year,
            extension=extension,
            filename_contains=filename_contains,
            path_contains=path_contains,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        logger.info(
            "[mcp_ricerca] list_documents completed source=s3 duration_ms=%s returned_documents=%s limit=%s sort_by=%s sort_order=%s query=%s year=%s extension=%s filename_contains=%s path_contains=%s bucket_name=%s context_source=%s",
            duration_ms,
            len(documents),
            limit,
            sort_by,
            sort_order,
            query or "<empty>",
            year or "<empty>",
            extension or "<empty>",
            filename_contains or "<empty>",
            path_contains or "<empty>",
            client_context.bucket_name or "<empty>",
            client_context.source,
        )
        return documents
    finally:
        _active_client_context.reset(reset_token)


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


def extract_text_from_pdf_excerpt(
    filepath: str,
    *,
    max_chars: int = 12000,
    max_pages: int = 8,
) -> str:
    if not pypdf:
        return "[ERROR] pypdf nao instalado."

    started_at = perf_counter()

    try:
        reader = pypdf.PdfReader(filepath)
        total_pages = len(reader.pages)
        texts = []
        extracted_chars = 0
        scanned_pages = 0

        for i, page in enumerate(reader.pages[: max(1, max_pages)]):
            scanned_pages = i + 1
            try:
                page_text = page.extract_text() or ""
                texts.append(page_text)
                extracted_chars += len(page_text)
                if extracted_chars >= max_chars:
                    break
            except Exception as e:
                logger.error(
                    "[PDF ERROR] Falha ao extrair texto da pagina %s no modo excerpt: %s",
                    i + 1,
                    e,
                    exc_info=True,
                )
                texts.append(f"[ERRO ao extrair texto da pagina {i + 1}]")

        result = "\n".join(texts)
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        logger.info(
            "[mcp_ricerca] extract_text_from_pdf_excerpt completed duration_ms=%s pages_scanned=%s total_pages=%s extracted_chars=%s",
            duration_ms,
            scanned_pages,
            total_pages,
            len(result),
        )
        if not result.strip():
            return (
                "[ERRO] Nao foi possivel extrair texto nativo deste PDF no modo excerpt. "
                "O documento pode ser escaneado ou conter apenas imagem; use mode='full' "
                "ou mode='ocr' apenas se a leitura ampliada for realmente necessaria."
            )
        return result
    except Exception as e:
        logger.error(
            "[PDF ERROR] Falha geral ao abrir PDF no modo excerpt: %s",
            e,
            exc_info=True,
        )
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
    ctx: Context,
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
    reset_token = _activate_client_context(ctx)
    started_at = perf_counter()
    try:
        client_context = _get_active_client_context()
        requested_filename = filename
        resolved_document = _resolve_document_from_index(filename)
        if not resolved_document:
            resolved_document = _resolve_document_from_s3(filename)
        resolved_filename = (
            resolved_document.get("key")
            if resolved_document and resolved_document.get("key")
            else filename
        )
        ext = os.path.splitext(resolved_filename)[1].lower()
        mode = (mode or "excerpt").strip().lower()
        if mode not in {"excerpt", "full", "ocr"}:
            mode = "excerpt"
        max_chars = max(1000, min(max_chars, 50000))

        if mode == "excerpt":
            preview = _get_document_preview_from_document(resolved_document)
            if not preview:
                preview = _get_document_preview_from_index(resolved_filename)
            if preview:
                returned_content = _truncate_text(
                    preview,
                    max_chars=max_chars,
                    metadata_prefix=(
                        f"filename={resolved_filename}\n"
                        f"mode=preview\n"
                        f"source=document_index"
                    ),
                )
                duration_ms = round((perf_counter() - started_at) * 1000, 2)
                logger.info(
                    "[mcp_ricerca] get_document completed source=preview filename=%s requested_filename=%s ext=%s mode=%s duration_ms=%s returned_chars=%s cost_tier=%s customer_code=%s bucket_name=%s context_source=%s",
                    resolved_filename,
                    requested_filename,
                    ext or "<none>",
                    mode,
                    duration_ms,
                    len(returned_content),
                    _read_cost_tier(
                        mode=mode,
                        ext=ext,
                        file_size_bytes=0,
                        source="preview",
                    ),
                    client_context.customer_code or "<empty>",
                    client_context.bucket_name or "<empty>",
                    client_context.source,
                )
                return returned_content

        with tempfile.NamedTemporaryFile(delete=True, suffix=ext) as tmp:
            try:
                s3.download_fileobj(client_context.bucket_name, resolved_filename, tmp)
            except ClientError as exc:
                error_code = exc.response.get("Error", {}).get("Code")
                duration_ms = round((perf_counter() - started_at) * 1000, 2)
                logger.warning(
                    "[mcp_ricerca] get_document_not_found filename=%s duration_ms=%s error_code=%s customer_code=%s bucket_name=%s context_source=%s",
                    resolved_filename,
                    duration_ms,
                    error_code or "<unknown>",
                    client_context.customer_code or "<empty>",
                    client_context.bucket_name or "<empty>",
                    client_context.source,
                )
                return (
                    f"[ERRO] Documento nao encontrado ou indisponivel: {requested_filename}. "
                    "Tente listar novamente os documentos antes de abrir este arquivo."
                )

            tmp.flush()
            file_size_bytes = tmp.tell()

            try:
                if ext in [".txt", ".md", ".csv"]:
                    tmp.seek(0)
                    content = tmp.read().decode("utf-8", errors="replace")
                elif ext == ".pdf":
                    if mode == "excerpt":
                        # Keep excerpt mode conservative on long PDFs when no index preview exists.
                        content = extract_text_from_pdf_excerpt(
                            tmp.name,
                            max_chars=min(max(max_chars * 2, 4000), 20000),
                        )
                    else:
                        content = extract_text_from_pdf(
                            tmp.name,
                            use_ocr=(mode == "ocr"),
                        )
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
                        f"filename={resolved_filename}\n"
                        f"mode={mode}\n"
                        f"file_extension={ext or '<none>'}\n"
                        f"file_size_bytes={file_size_bytes}"
                    )
                    returned_content = _truncate_text(
                        content,
                        max_chars=max_chars,
                        metadata_prefix=metadata_prefix,
                    )

                if content and not content.startswith("[ERRO]") and not content.startswith("[ERROR]"):
                    compact_preview = " ".join(content.split())[:6000].strip()
                    _persist_document_content_to_index(
                        document_key=resolved_filename,
                        text_preview=compact_preview,
                        extracted_text=content,
                    )

                duration_ms = round((perf_counter() - started_at) * 1000, 2)
                logger.info(
                    "[mcp_ricerca] get_document completed filename=%s requested_filename=%s ext=%s mode=%s duration_ms=%s file_size_bytes=%s extracted_chars=%s returned_chars=%s cost_tier=%s customer_code=%s bucket_name=%s context_source=%s",
                    resolved_filename,
                    requested_filename,
                    ext or "<none>",
                    mode,
                    duration_ms,
                    file_size_bytes,
                    len(content),
                    len(returned_content),
                    _read_cost_tier(
                        mode=mode,
                        ext=ext,
                        file_size_bytes=file_size_bytes,
                        source="download",
                    ),
                    client_context.customer_code or "<empty>",
                    client_context.bucket_name or "<empty>",
                    client_context.source,
                )
                return returned_content
            except Exception as e:
                logger.error(
                    "[ERROR] Falha ao processar arquivo %s: %s",
                    resolved_filename,
                    e,
                    exc_info=True,
                )
                return f"[ERRO] Nao foi possivel processar o arquivo: {e}"
    finally:
        _active_client_context.reset(reset_token)


if __name__ == "__main__":
    logger.info("Servidor MCP iniciado em http://localhost:7000/mcp")
    mcp.run(host="0.0.0.0", port=7000, transport="sse")
