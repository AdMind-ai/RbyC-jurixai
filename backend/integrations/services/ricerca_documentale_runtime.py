from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Optional

from django.conf import settings

from core.services.document_retrieval.intent_classifier import (
    classify_document_search_intent,
)
from core.services.document_retrieval.presearch import (
    build_retrieval_guidance_candidates,
)
from core.services.document_retrieval.prompt_context import (
    build_document_search_input,
)
from core.services.document_retrieval.retrieval_strategies import (
    get_retrieval_strategy,
)
from integrations.services.mcp_auth import build_mcp_access_token


@dataclass(frozen=True)
class RicercaDocumentaleRequestContext:
    prompt: str
    prompt_length: int
    intent_classification: Any
    retrieval_strategy: Any
    presearch_candidates: list[Any]
    related_approval_candidates: list[Any]
    model_input: str
    bucket_name: str | None
    client_name: str | None
    customer_code: str
    mcp_token: str | None


@dataclass(frozen=True)
class RicercaDocumentaleResponsePayload:
    raw_output: str
    raw_output_length: int
    response_text: str
    response_keys: list[str]


def _looks_like_document_key(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip()
    if not normalized or normalized.endswith("/"):
        return False
    return "/" in normalized or "." in normalized


def _coerce_to_plain_data(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)

    for method_name in ("model_dump", "dict"):
        method = getattr(value, method_name, None)
        if callable(method):
            try:
                return method()
            except Exception:
                continue

    if hasattr(value, "__dict__"):
        try:
            return vars(value)
        except Exception:
            return value
    return value


def collect_document_keys_from_payload(payload: Any) -> list[str]:
    from core.utils.common import safe_load_json

    collected: list[str] = []
    seen_ids: set[int] = set()

    def visit(node: Any) -> None:
        node = _coerce_to_plain_data(node)
        node_id = id(node)
        if node_id in seen_ids:
            return
        seen_ids.add(node_id)

        if node is None:
            return

        if isinstance(node, str):
            text = node.strip()
            if not text:
                return
            parsed = None
            if text.startswith("{") or text.startswith("["):
                try:
                    parsed = safe_load_json(text)
                except Exception:
                    parsed = None
            if parsed not in (None, text):
                visit(parsed)
            return

        if isinstance(node, Mapping):
            keys_value = node.get("keys")
            if isinstance(keys_value, (list, tuple)):
                for item in keys_value:
                    if _looks_like_document_key(item):
                        collected.append(item.strip())

            key_value = node.get("key")
            if _looks_like_document_key(key_value):
                collected.append(key_value.strip())

            path_value = node.get("path")
            if _looks_like_document_key(path_value):
                collected.append(path_value.strip())

            output_value = node.get("output")
            if output_value is not None:
                visit(output_value)

            content_value = node.get("content")
            if content_value is not None:
                visit(content_value)

            skipped_child_ids = {
                id(value)
                for value in (
                    keys_value,
                    key_value,
                    path_value,
                    output_value,
                    content_value,
                )
                if value is not None
            }
            for child in node.values():
                if id(child) in skipped_child_ids:
                    continue
                visit(child)
            return

        if isinstance(node, Sequence) and not isinstance(node, (str, bytes, bytearray)):
            for item in node:
                visit(item)

    visit(payload)

    deduped: list[str] = []
    seen_keys: set[str] = set()
    for item in collected:
        if item not in seen_keys:
            seen_keys.add(item)
            deduped.append(item)
    return deduped


def build_ricerca_documentale_request_context(
    *,
    prompt: str,
    integration_client: Any,
) -> RicercaDocumentaleRequestContext:
    intent_classification = classify_document_search_intent(prompt)
    retrieval_strategy = get_retrieval_strategy(
        intent_classification.intent_type
    )
    retrieval_guidance = build_retrieval_guidance_candidates(
        user_input=prompt,
        intent_classification=intent_classification,
        retrieval_strategy=retrieval_strategy,
        customer_code=(
            getattr(integration_client, "customer_code", None) or ""
        ),
    )
    presearch_candidates = retrieval_guidance.presearch_candidates
    related_approval_candidates = (
        retrieval_guidance.related_approval_candidates
    )
    model_input = build_document_search_input(
        prompt,
        intent_classification,
        retrieval_strategy,
        presearch_candidates=presearch_candidates,
        related_approval_candidates=related_approval_candidates,
    )

    return RicercaDocumentaleRequestContext(
        prompt=prompt,
        prompt_length=len(prompt or ""),
        intent_classification=intent_classification,
        retrieval_strategy=retrieval_strategy,
        presearch_candidates=presearch_candidates,
        related_approval_candidates=related_approval_candidates,
        model_input=model_input,
        bucket_name=(
            getattr(integration_client, "bucket_name", None)
            or getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
        ),
        client_name=getattr(integration_client, "client_name", None),
        customer_code=getattr(integration_client, "customer_code", None) or "",
        mcp_token=(
            build_mcp_access_token(integration_client)
            if integration_client is not None
            else None
        ),
    )


def build_ricerca_documentale_mcp_tool(*, mcp_token: str | None) -> dict[str, Any]:
    tool = {
        "type": "mcp",
        "server_label": "rbyc",
        "server_description": "Ferramenta para buscar documentos indexados, listar metadados e consultar trechos quando necessario",
        "server_url": settings.MCP_SERVER_URL,
        "allowed_tools": [
            "search_documents",
            "list_documents",
            "get_document",
        ],
        "require_approval": "never",
    }
    if mcp_token:
        tool["headers"] = {
            "Authorization": f"Bearer {mcp_token}",
        }
    return tool


def extract_ricerca_documentale_response_payload(response: Any) -> RicercaDocumentaleResponsePayload:
    from core.utils.common import safe_load_json

    if isinstance(response, str):
        raw_output = response
    else:
        try:
            raw_output = getattr(response, "output_text", None)
        except Exception:
            raw_output = str(response)

    raw_output = raw_output or ""
    raw_output_length = len(raw_output)

    try:
        json_res: Optional[Any] = safe_load_json(raw_output)
    except Exception:
        json_res = None

    response_text = ""
    response_keys: list[str] = []

    if isinstance(json_res, dict):
        response_text = (
            json_res.get("response_text")
            or json_res.get("response")
            or json_res.get("output_text")
            or json_res.get("text")
            or raw_output
        )
        if "keys" in json_res and isinstance(json_res["keys"], (list, tuple)):
            response_keys = list(json_res["keys"])
    elif json_res is None:
        response_text = raw_output
    else:
        response_text = (
            getattr(json_res, "response", None)
            or getattr(json_res, "output_text", None)
            or str(json_res)
        )

    if response_text is None:
        response_text = ""
    elif not isinstance(response_text, str):
        response_text = str(response_text)

    if not response_keys:
        response_keys = collect_document_keys_from_payload(response)

    return RicercaDocumentaleResponsePayload(
        raw_output=raw_output,
        raw_output_length=raw_output_length,
        response_text=response_text,
        response_keys=response_keys,
    )
