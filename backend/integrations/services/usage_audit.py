from __future__ import annotations

import logging
from typing import Any

from integrations.models import (
    IntegrationApiKey,
    IntegrationUsageRecord,
    IntegrationUsageTool,
)

logger = logging.getLogger(__name__)


def record_integration_ricerca_documentale_usage(
    *,
    auth: Any,
    integration_client,
    request_id: str,
    conversation_id: str,
    prompt: str,
    request_context,
    response_text: str,
    documents_count: int,
    metadata: dict | None = None,
):
    metadata = metadata or {}
    api_key = auth if isinstance(auth, IntegrationApiKey) else None

    if api_key:
        auth_mode = "api_key"
        auth_identifier = (
            api_key.description
            or api_key.environment
            or ""
        )
    elif auth:
        auth_mode = "legacy_shared_key"
        auth_identifier = "legacy_shared_key"
    else:
        auth_mode = "unknown"
        auth_identifier = ""

    safe_metadata = {
        "bucket_name": getattr(request_context, "bucket_name", "") or "",
        "customer_code": getattr(request_context, "customer_code", "") or "",
        "client_name": getattr(request_context, "client_name", "") or "",
        **metadata,
    }

    try:
        return IntegrationUsageRecord.objects.create(
            client=integration_client,
            api_key=api_key,
            tool=IntegrationUsageTool.RICERCA_DOCUMENTALE,
            request_id=request_id or "",
            conversation_id=conversation_id or "",
            auth_mode=auth_mode,
            auth_identifier=auth_identifier,
            intent_type=getattr(
                getattr(request_context, "intent_classification", None),
                "intent_type",
                "",
            )
            or "",
            prompt_length=len(prompt or ""),
            model_input_length=len(getattr(request_context, "model_input", "") or ""),
            response_text_length=len(response_text or ""),
            documents_count=max(int(documents_count or 0), 0),
            metadata=safe_metadata,
        )
    except Exception:
        logger.exception(
            "Erro ao registrar auditoria de uso da integracao",
            extra={
                "request_id": request_id,
                "customer_code": getattr(request_context, "customer_code", None),
                "auth_mode": auth_mode,
            },
        )
        return None
