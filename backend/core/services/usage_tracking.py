from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.utils import timezone

from core.models.usage import UsageRecord

logger = logging.getLogger(__name__)


@dataclass
class UsageRecordingResult:
    record: Optional[UsageRecord]


class UsageTrackingService:
    @classmethod
    def record_usage_event(
        cls,
        *,
        user,
        tool: str,
        sub_tool: Optional[str] = None,
        quantity: Decimal | int | float = 1,
        company=None,
        occurred_at=None,
        metadata: Optional[dict] = None,
        raise_on_error: bool = False,
    ) -> UsageRecordingResult | None:
        metadata = metadata or {}
        occurred_at = occurred_at or timezone.now()

        try:
            quantity_decimal = cls._to_decimal(quantity, default=Decimal("1"))
            safe_metadata = cls._sanitize_metadata(metadata)

            with transaction.atomic():
                record = UsageRecord.objects.create(
                    user=user,
                    company=company,
                    tool=tool,
                    sub_tool=sub_tool,
                    occurred_at=occurred_at,
                    quantity=quantity_decimal,
                    metadata=safe_metadata,
                )

            return UsageRecordingResult(record=record)
        except Exception:
            logger.exception(
                "Erro ao registrar evento de uso",
                extra={
                    "user_id": getattr(user, "id", None),
                    "tool": tool,
                    "sub_tool": sub_tool,
                },
            )
            if raise_on_error:
                raise
            return None

    @staticmethod
    def _to_decimal(value, default: Optional[Decimal] = None) -> Decimal:
        if value is None:
            if default is not None:
                return default
            raise ValueError("Valor decimal nao fornecido")
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    @classmethod
    def _sanitize_metadata(cls, value):
        if isinstance(value, dict):
            return {str(k): cls._sanitize_metadata(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [cls._sanitize_metadata(v) for v in value]
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)
