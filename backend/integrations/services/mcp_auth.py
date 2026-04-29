from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from django.conf import settings

from integrations.models import IntegrationClient


MCP_AUTH_ALGORITHM = "HS256"


def build_mcp_access_token(client: IntegrationClient) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(
        seconds=max(30, int(settings.MCP_INTERNAL_AUTH_TTL_SECONDS))
    )
    payload = {
        "iss": settings.MCP_INTERNAL_AUTH_ISSUER,
        "aud": settings.MCP_INTERNAL_AUTH_AUDIENCE,
        "client_id": client.pk,
        "customer_code": client.customer_code,
        "bucket_name": client.bucket_name,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(
        payload,
        settings.MCP_INTERNAL_AUTH_SECRET,
        algorithm=MCP_AUTH_ALGORITHM,
    )


def decode_mcp_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.MCP_INTERNAL_AUTH_SECRET,
        algorithms=[MCP_AUTH_ALGORITHM],
        audience=settings.MCP_INTERNAL_AUTH_AUDIENCE,
        issuer=settings.MCP_INTERNAL_AUTH_ISSUER,
    )
