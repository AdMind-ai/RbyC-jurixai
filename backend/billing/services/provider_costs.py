from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from billing.models import (
    ProviderCostProvider,
    ProviderCostSource,
    ProviderMonthlyCost,
)
from core.services.usage_service import compute_month_bounds

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderCostTotal:
    amount: Decimal
    currency: str
    costs: list[ProviderMonthlyCost]


class ProviderCostService:
    OPENAI_COSTS_URL = "https://api.openai.com/v1/organization/costs"

    @classmethod
    def refresh_monthly_costs(cls, period_month: date) -> list[ProviderMonthlyCost]:
        return [
            cls.refresh_openai_cost(period_month),
            cls.ensure_not_configured_cost(
                provider=ProviderCostProvider.GEMINI,
                period_month=period_month,
                reason="Gemini billing integration is not configured yet.",
            ),
            cls.ensure_not_configured_cost(
                provider=ProviderCostProvider.PERPLEXITY,
                period_month=period_month,
                reason="Perplexity billing integration is not configured yet.",
            ),
        ]

    @classmethod
    def get_total_for_month(cls, period_month: date, *, refresh: bool = True) -> ProviderCostTotal:
        costs = cls.refresh_monthly_costs(period_month) if refresh else list(
            ProviderMonthlyCost.objects.filter(period_month=period_month)
        )
        billing_currency = cls.billing_currency()
        total = Decimal("0.0000")

        for cost in costs:
            total += cost.total_with_vat

        return ProviderCostTotal(
            amount=total.quantize(Decimal("0.01"), ROUND_HALF_UP),
            currency=billing_currency,
            costs=costs,
        )

    @classmethod
    def refresh_openai_cost(cls, period_month: date) -> ProviderMonthlyCost:
        admin_key = getattr(settings, "OPENAI_ADMIN_KEY", None)
        if not admin_key:
            return cls.ensure_not_configured_cost(
                provider=ProviderCostProvider.OPENAI,
                period_month=period_month,
                reason="OPENAI_ADMIN_KEY is not configured.",
                external_project_id=cls.openai_project_id(),
            )

        payload = cls._fetch_openai_cost_payload(period_month, admin_key)
        amount, currency = cls._parse_openai_cost_payload(payload)
        return cls.upsert_provider_cost(
            provider=ProviderCostProvider.OPENAI,
            period_month=period_month,
            amount=amount,
            currency=cls.billing_currency(),
            source=ProviderCostSource.ACTUAL_API,
            external_project_id=cls.openai_project_id(),
            raw_payload=payload,
            metadata={"provider_currency": currency},
        )

    @classmethod
    def ensure_not_configured_cost(
        cls,
        *,
        provider: str,
        period_month: date,
        reason: str,
        external_project_id: Optional[str] = None,
    ) -> ProviderMonthlyCost:
        return cls.upsert_provider_cost(
            provider=provider,
            period_month=period_month,
            amount=Decimal("0"),
            currency=cls.billing_currency(),
            source=ProviderCostSource.NOT_CONFIGURED,
            external_project_id=external_project_id,
            metadata={"reason": reason},
        )

    @classmethod
    def upsert_provider_cost(
        cls,
        *,
        provider: str,
        period_month: date,
        amount: Decimal,
        currency: str,
        source: str,
        external_project_id: Optional[str] = None,
        raw_payload: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> ProviderMonthlyCost:
        with transaction.atomic():
            cost, _ = ProviderMonthlyCost.objects.select_for_update().get_or_create(
                provider=provider,
                period_month=period_month,
            )
            provider_amount = amount.quantize(Decimal("0.0001"), ROUND_HALF_UP)
            markup_percentage = cls.markup_percentage()
            vat_percentage = cls.vat_percentage()
            amount_with_markup = (
                provider_amount * (Decimal("1") + (markup_percentage / Decimal("100")))
            ).quantize(Decimal("0.0001"), ROUND_HALF_UP)
            total_with_vat = (
                amount_with_markup * (Decimal("1") + (vat_percentage / Decimal("100")))
            ).quantize(Decimal("0.0001"), ROUND_HALF_UP)

            cost.provider_amount = provider_amount
            cost.markup_percentage = markup_percentage
            cost.amount_with_markup = amount_with_markup
            cost.vat_percentage = vat_percentage
            cost.total_with_vat = total_with_vat
            cost.amount = total_with_vat
            cost.currency = currency.upper()
            cost.source = source
            cost.external_project_id = external_project_id
            cost.fetched_at = timezone.now()
            cost.raw_payload = raw_payload or {}
            cost.metadata = metadata or {}
            cost.save()
            return cost

    @classmethod
    def _fetch_openai_cost_payload(cls, period_month: date, admin_key: str) -> dict:
        _, start_dt, end_dt = compute_month_bounds(period_month.strftime("%Y-%m"))
        start_time = int(start_dt.timestamp())
        end_time = int(end_dt.timestamp())
        headers = {"Authorization": f"Bearer {admin_key}"}
        project_id = cls.openai_project_id()
        params = [
            ("start_time", start_time),
            ("end_time", end_time),
            ("bucket_width", "1d"),
            ("limit", 180),
            ("group_by[]", "project_id"),
            ("group_by[]", "line_item"),
        ]
        if project_id:
            params.append(("project_ids[]", project_id))

        all_buckets = []
        next_page = None
        while True:
            request_params = list(params)
            if next_page:
                request_params.append(("page", next_page))
            response = requests.get(
                cls.OPENAI_COSTS_URL,
                headers=headers,
                params=request_params,
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            all_buckets.extend(payload.get("data", []))
            next_page = payload.get("next_page")
            if not payload.get("has_more") or not next_page:
                payload["data"] = all_buckets
                return payload

    @classmethod
    def _parse_openai_cost_payload(cls, payload: dict) -> tuple[Decimal, str]:
        project_id = cls.openai_project_id()
        total = Decimal("0")
        currency = cls.billing_currency()

        for bucket in payload.get("data", []):
            for result in bucket.get("results", []):
                if project_id and result.get("project_id") not in (None, project_id):
                    continue
                amount = result.get("amount") or {}
                value = amount.get("value")
                if value is None:
                    continue
                currency = (amount.get("currency") or currency).upper()
                total += Decimal(str(value))

        return total.quantize(Decimal("0.0001"), ROUND_HALF_UP), currency

    @staticmethod
    def billing_currency() -> str:
        return getattr(settings, "BILLING_DEFAULT_CURRENCY", "EUR").upper()

    @staticmethod
    def markup_percentage() -> Decimal:
        return Decimal(str(getattr(settings, "BILLING_COMPANY_MARKUP_PERCENTAGE", "20")))

    @staticmethod
    def vat_percentage() -> Decimal:
        return Decimal(str(getattr(settings, "BILLING_IVA_PERCENTAGE", "22")))

    @staticmethod
    def openai_project_id() -> Optional[str]:
        return getattr(settings, "OPENAI_COSTS_PROJECT_ID", None) or getattr(
            settings,
            "OPENAI_PROJECT_ID",
            None,
        )
