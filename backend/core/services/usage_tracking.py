from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional, Union

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.models.usage import UsageRate, UsageRecord, UsageTool

logger = logging.getLogger(__name__)


@dataclass
class UsageRecordingResult:
    record: Optional[UsageRecord]
    unit_price: Decimal
    total_cost: Decimal
    used_rate_id: Optional[int]


class UsageTrackingService:
    @classmethod
    def record_usage_event(
        cls,
        *,
        user,
        tool: str,
        sub_tool: Optional[str] = None,
        quantity: Union[Decimal, int, float] = 1,
        unit_price: Optional[Union[Decimal, float, int]] = None,
        company=None,
        occurred_at=None,
        metadata: Optional[dict] = None,
        raise_on_error: bool = False,
    ) -> UsageRecordingResult | None:
        metadata = metadata or {}
        occurred_at = occurred_at or timezone.now()

        try:
            quantity_decimal = cls._to_decimal(quantity, default=Decimal("1"))
            resolved_rate = None
            if unit_price is not None:
                unit_price_decimal = cls._to_decimal(unit_price)
            else:
                unit_price_decimal, resolved_rate = cls._resolve_unit_price(
                    tool, sub_tool, occurred_at.date()
                )
            total_cost = (quantity_decimal * unit_price_decimal).quantize(Decimal("0.0001"))
            safe_metadata = cls._sanitize_metadata(metadata)

            with transaction.atomic():
                record = UsageRecord.objects.create(
                    user=user,
                    company=company,
                    tool=tool,
                    sub_tool=sub_tool,
                    occurred_at=occurred_at,
                    quantity=quantity_decimal,
                    unit_price_eur=unit_price_decimal,
                    total_cost_eur=total_cost,
                    metadata=safe_metadata,
                )

            return UsageRecordingResult(
                record=record,
                unit_price=unit_price_decimal,
                total_cost=total_cost,
                used_rate_id=resolved_rate.id if resolved_rate else None,
            )
        except Exception:  # pragma: no cover - best-effort safeguard
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
            raise ValueError("Valor decimal não fornecido")
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    @classmethod
    def _resolve_unit_price(
        cls, tool: str, sub_tool: Optional[str], reference_date: date
    ) -> tuple[Decimal, Optional[UsageRate]]:
        rate = cls._get_applicable_rate(tool, sub_tool, reference_date)
        if rate:
            return rate.unit_price_eur, rate

        configured_price = cls._get_configured_unit_price(tool, sub_tool)
        if configured_price is not None:
            return configured_price, None

        logger.warning(
            "Tarifa não encontrada para %s/%s em %s. Aplicando 0.",
            tool,
            sub_tool,
            reference_date,
        )
        return Decimal("0"), None

    @classmethod
    def _get_configured_unit_price(
        cls, tool: str, sub_tool: Optional[str]
    ) -> Optional[Decimal]:
        configured = getattr(settings, "USAGE_DEFAULT_PRICES", {})

        def normalize(val):
            return None if val is None else cls._to_decimal(val)

        if sub_tool and isinstance(configured.get(tool), dict):
            return normalize(configured[tool].get(sub_tool))

        raw = configured.get(tool)
        if raw is not None and not isinstance(raw, dict):
            return normalize(raw)

        key = f"{tool}:{sub_tool}" if sub_tool else tool
        if key in configured:
            return normalize(configured[key])
        return None

    @staticmethod
    def _get_applicable_rate(tool: str, sub_tool: Optional[str], reference_date: date) -> UsageRate | None:
        filters = Q(tool=tool)
        if sub_tool:
            filters &= Q(sub_tool=sub_tool)
        else:
            filters &= Q(sub_tool__isnull=True)

        return (
            UsageRate.objects.filter(filters)
            .filter(effective_from__lte=reference_date)
            .filter(Q(effective_to__gte=reference_date) | Q(effective_to__isnull=True))
            .order_by("-effective_from")
            .first()
        )

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
