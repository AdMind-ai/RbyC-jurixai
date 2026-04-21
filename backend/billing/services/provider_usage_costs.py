from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from django.conf import settings
from django.db.models import Count, Sum
from django.utils import timezone

from billing.models import ProviderCostProvider, ProviderUsageCost
from core.services.usage_service import compute_month_bounds


@dataclass(frozen=True)
class ProviderUsageCostAggregate:
    amount: Decimal
    currency: str
    entry_count: int
    provider_currency: Optional[str]


class ProviderUsageCostService:
    @classmethod
    def record_perplexity_usage_cost(
        cls,
        *,
        usage_payload: Optional[dict],
        usage_record=None,
        external_request_id: Optional[str] = None,
        occurred_at=None,
        metadata: Optional[dict] = None,
    ) -> Optional[ProviderUsageCost]:
        if not usage_payload:
            return None

        cost_payload = usage_payload.get("cost") or {}
        total_cost = cost_payload.get("total_cost")
        if total_cost is None:
            return None

        occurred_at = occurred_at or getattr(usage_record, "occurred_at", None) or timezone.now()
        amount = Decimal(str(total_cost)).quantize(Decimal("0.0001"), ROUND_HALF_UP)
        provider_currency = cost_payload.get("currency") or "USD"
        defaults = {
            "usage_record": usage_record,
            "occurred_at": occurred_at,
            "amount": amount,
            "currency": cls.billing_currency(),
            "provider_currency": provider_currency,
            "raw_payload": usage_payload,
            "metadata": metadata or {},
        }

        if external_request_id:
            cost, _ = ProviderUsageCost.objects.update_or_create(
                provider=ProviderCostProvider.PERPLEXITY,
                external_request_id=external_request_id,
                defaults=defaults,
            )
            return cost

        return ProviderUsageCost.objects.create(
            provider=ProviderCostProvider.PERPLEXITY,
            external_request_id=None,
            **defaults,
        )

    @classmethod
    def get_provider_monthly_total(
        cls,
        *,
        provider: str,
        period_month: date,
    ) -> ProviderUsageCostAggregate:
        _, start_dt, end_dt = compute_month_bounds(period_month.strftime("%Y-%m"))
        queryset = ProviderUsageCost.objects.filter(
            provider=provider,
            occurred_at__gte=start_dt,
            occurred_at__lt=end_dt,
        )
        totals = queryset.aggregate(
            total_amount=Sum("amount", default=Decimal("0")),
            entry_count=Count("id"),
        )
        provider_currency = queryset.values_list("provider_currency", flat=True).first()
        return ProviderUsageCostAggregate(
            amount=Decimal(str(totals["total_amount"] or Decimal("0"))).quantize(
                Decimal("0.0001"), ROUND_HALF_UP
            ),
            currency=cls.billing_currency(),
            entry_count=totals["entry_count"] or 0,
            provider_currency=provider_currency,
        )

    @staticmethod
    def extract_perplexity_request_id(chunk) -> Optional[str]:
        return ProviderUsageCostService._get_attr(chunk, "id")

    @staticmethod
    def extract_perplexity_usage_metadata(chunk) -> Optional[dict]:
        usage = ProviderUsageCostService._get_attr(chunk, "usage")
        if not usage:
            return None

        cost = ProviderUsageCostService._get_attr(usage, "cost")
        metadata = {
            "prompt_tokens": ProviderUsageCostService._get_attr(usage, "prompt_tokens"),
            "completion_tokens": ProviderUsageCostService._get_attr(usage, "completion_tokens"),
            "total_tokens": ProviderUsageCostService._get_attr(usage, "total_tokens"),
            "citation_tokens": ProviderUsageCostService._get_attr(usage, "citation_tokens"),
            "num_search_queries": ProviderUsageCostService._get_attr(usage, "num_search_queries"),
            "reasoning_tokens": ProviderUsageCostService._get_attr(usage, "reasoning_tokens"),
            "search_context_size": ProviderUsageCostService._get_attr(usage, "search_context_size"),
        }
        cost_metadata = {
            "input_tokens_cost": ProviderUsageCostService._decimal_to_float(
                ProviderUsageCostService._get_attr(cost, "input_tokens_cost")
            ),
            "output_tokens_cost": ProviderUsageCostService._decimal_to_float(
                ProviderUsageCostService._get_attr(cost, "output_tokens_cost")
            ),
            "total_cost": ProviderUsageCostService._decimal_to_float(
                ProviderUsageCostService._get_attr(cost, "total_cost")
            ),
            "citation_tokens_cost": ProviderUsageCostService._decimal_to_float(
                ProviderUsageCostService._get_attr(cost, "citation_tokens_cost")
            ),
            "reasoning_tokens_cost": ProviderUsageCostService._decimal_to_float(
                ProviderUsageCostService._get_attr(cost, "reasoning_tokens_cost")
            ),
            "request_cost": ProviderUsageCostService._decimal_to_float(
                ProviderUsageCostService._get_attr(cost, "request_cost")
            ),
            "search_queries_cost": ProviderUsageCostService._decimal_to_float(
                ProviderUsageCostService._get_attr(cost, "search_queries_cost")
            ),
            "currency": "USD",
        }
        if any(value is not None for value in cost_metadata.values()):
            metadata["cost"] = cost_metadata

        sanitized = {key: value for key, value in metadata.items() if value is not None}
        return sanitized or None

    @staticmethod
    def billing_currency() -> str:
        return getattr(settings, "BILLING_DEFAULT_CURRENCY", "EUR").upper()

    @staticmethod
    def _get_attr(value, key: str):
        if value is None:
            return None
        if isinstance(value, dict):
            return value.get(key)
        return getattr(value, key, None)

    @staticmethod
    def _decimal_to_float(value):
        if value is None:
            return None
        return float(Decimal(str(value)))