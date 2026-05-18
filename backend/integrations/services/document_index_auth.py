from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed

from integrations.services.mcp_auth import decode_mcp_access_token


def resolve_internal_document_index_customer_code(request) -> str:
    authorization = (request.headers.get("Authorization") or "").strip()
    if not authorization.lower().startswith("bearer "):
        raise AuthenticationFailed("Missing MCP bearer token.")

    token = authorization[7:].strip()
    if not token:
        raise AuthenticationFailed("Missing MCP bearer token.")

    try:
        payload = decode_mcp_access_token(token)
    except Exception as exc:
        raise AuthenticationFailed("Invalid MCP bearer token.") from exc

    customer_code = str(payload.get("customer_code") or "").strip()
    if not customer_code:
        raise AuthenticationFailed("MCP bearer token missing customer_code.")

    query_customer_code = (request.query_params.get("customer_code") or "").strip()
    if query_customer_code and query_customer_code != customer_code:
        raise AuthenticationFailed("customer_code mismatch for MCP bearer token.")

    return customer_code


def validate_internal_document_index_request(request) -> str:
    expected_key = getattr(settings, "DOCUMENT_INDEX_API_KEY", None)
    provided_key = request.headers.get("X-Internal-API-Key")
    if not expected_key or provided_key != expected_key:
        raise AuthenticationFailed("Unauthorized internal document index request.")

    return resolve_internal_document_index_customer_code(request)
