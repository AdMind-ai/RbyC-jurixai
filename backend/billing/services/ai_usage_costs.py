from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from billing.models import BillingInvoice, ProviderCostSource
from billing.services.provider_costs import ProviderCostService
from core.models.vera_usage_model import VeraProvider, VeraUsageRecord
from core.services.vera_cost_sync_service import VeraCostSyncService


MONEY_QUANT = Decimal("0.01")
INTERNAL_QUANT = Decimal("0.0001")


@dataclass(frozen=True)
class AIProviderCostLine:
    provider: str
    provider_amount: Decimal
    amount_with_markup: Decimal
    total_with_vat: Decimal
    currency: str
    source: str
    fetched_at: Optional[object] = None
    metadata: Optional[dict] = None


@dataclass(frozen=True)
class AIMonthlyCostSummary:
    period_month: date
    currency: str
    rbyc_raw: Decimal
    vera_openai_raw: Decimal
    vera_anthropic_raw: Decimal
    vera_raw: Decimal
    rbyc_with_markup: Decimal
    vera_with_markup: Decimal
    total_with_markup: Decimal
    total_with_vat: Decimal
    vera_total_with_vat: Decimal
    rbyc_markup_percentage: Decimal
    vera_markup_percentage: Decimal
    vat_percentage: Decimal
    is_fresh: bool
    refresh_error: Optional[str]
    provider_costs: list[AIProviderCostLine]


class AIUsageCostService:
    @classmethod
    def build_monthly_summary(
        cls,
        period_month: date,
        *,
        refresh_rbyc: bool = False,
        refresh_vera: bool = False,
    ) -> AIMonthlyCostSummary:
        period_month = period_month.replace(day=1)
        currency = cls.currency()
        is_fresh = True
        refresh_error = None

        try:
            rbyc_cost = ProviderCostService.refresh_openai_cost(period_month) if refresh_rbyc else (
                ProviderCostService.get_openai_cost(period_month)
            )
        except Exception as exc:
            saved_cost = ProviderCostService.get_openai_cost(period_month)
            if not saved_cost:
                raise
            rbyc_cost = saved_cost
            is_fresh = False
            refresh_error = str(exc)

        if refresh_vera:
            try:
                cls.refresh_vera_costs_for_month(period_month)
            except Exception as exc:
                is_fresh = False
                refresh_error = cls._join_errors(refresh_error, str(exc))

        rbyc_raw = cls._decimal(getattr(rbyc_cost, "provider_amount", Decimal("0")))
        vera_openai_raw = cls._sum_vera_cost(period_month, VeraProvider.OPENAI)
        vera_anthropic_raw = cls._sum_vera_cost(period_month, VeraProvider.ANTHROPIC)
        vera_raw = vera_openai_raw + vera_anthropic_raw

        rbyc_markup = cls.rbyc_markup_percentage()
        vera_markup = cls.vera_markup_percentage()
        vat = cls.vat_percentage()

        rbyc_with_markup = cls._apply_percentage(rbyc_raw, rbyc_markup)
        vera_with_markup = cls._apply_percentage(vera_raw, vera_markup)
        total_with_markup = rbyc_with_markup + vera_with_markup
        total_with_vat = cls._apply_percentage(total_with_markup, vat).quantize(
            MONEY_QUANT,
            ROUND_HALF_UP,
        )
        vera_total_with_vat = cls._apply_percentage(vera_with_markup, vat).quantize(
            MONEY_QUANT,
            ROUND_HALF_UP,
        )

        provider_costs = [
            AIProviderCostLine(
                provider="openai_rbyc",
                provider_amount=rbyc_raw,
                amount_with_markup=rbyc_with_markup,
                total_with_vat=cls._apply_percentage(rbyc_with_markup, vat),
                currency=currency,
                source=getattr(rbyc_cost, "source", ProviderCostSource.NOT_CONFIGURED),
                fetched_at=getattr(rbyc_cost, "fetched_at", None),
                metadata={
                    **(getattr(rbyc_cost, "metadata", None) or {}),
                    "label": "OpenAI RbyC",
                    "markup_percentage": str(rbyc_markup),
                    "external_project_id": getattr(rbyc_cost, "external_project_id", None),
                },
            ),
            AIProviderCostLine(
                provider="vera_openai",
                provider_amount=vera_openai_raw,
                amount_with_markup=cls._apply_percentage(vera_openai_raw, vera_markup),
                total_with_vat=cls._apply_percentage(
                    cls._apply_percentage(vera_openai_raw, vera_markup),
                    vat,
                ),
                currency=currency,
                source=ProviderCostSource.ACTUAL_API,
                metadata={
                    "label": "Vera OpenAI",
                    "markup_percentage": str(vera_markup),
                },
            ),
            AIProviderCostLine(
                provider="vera_anthropic",
                provider_amount=vera_anthropic_raw,
                amount_with_markup=cls._apply_percentage(vera_anthropic_raw, vera_markup),
                total_with_vat=cls._apply_percentage(
                    cls._apply_percentage(vera_anthropic_raw, vera_markup),
                    vat,
                ),
                currency=currency,
                source=ProviderCostSource.ACTUAL_API,
                metadata={
                    "label": "Vera Anthropic",
                    "markup_percentage": str(vera_markup),
                },
            ),
        ]

        return AIMonthlyCostSummary(
            period_month=period_month,
            currency=currency,
            rbyc_raw=rbyc_raw,
            vera_openai_raw=vera_openai_raw,
            vera_anthropic_raw=vera_anthropic_raw,
            vera_raw=vera_raw,
            rbyc_with_markup=rbyc_with_markup,
            vera_with_markup=vera_with_markup,
            total_with_markup=total_with_markup.quantize(MONEY_QUANT, ROUND_HALF_UP),
            total_with_vat=total_with_vat,
            vera_total_with_vat=vera_total_with_vat,
            rbyc_markup_percentage=rbyc_markup,
            vera_markup_percentage=vera_markup,
            vat_percentage=vat,
            is_fresh=is_fresh,
            refresh_error=refresh_error,
            provider_costs=provider_costs,
        )

    @classmethod
    def serialize_for_billing(
        cls,
        period_month: date,
        *,
        refresh_rbyc: bool = False,
        refresh_vera: bool = False,
    ) -> dict:
        summary = cls.build_monthly_summary(
            period_month,
            refresh_rbyc=refresh_rbyc,
            refresh_vera=refresh_vera,
        )
        invoice = BillingInvoice.objects.filter(period_month=summary.period_month).first()

        return {
            "periodMonth": summary.period_month.strftime("%Y-%m"),
            "amountEur": float(summary.total_with_vat),
            "totalWithVatEur": float(summary.total_with_vat),
            "veraTotalWithVatEur": float(summary.vera_total_with_vat),
            "currency": summary.currency,
            "chargeDate": cls.charge_date_for_period(summary.period_month),
            "isFresh": summary.is_fresh,
            "refreshError": summary.refresh_error,
            "invoice": cls.serialize_invoice(invoice),
            "providerCosts": [
                {
                    "provider": line.provider,
                    "providerAmount": float(line.provider_amount),
                    "amountWithMarkup": float(line.amount_with_markup),
                    "totalWithVat": float(line.total_with_vat),
                    "currency": line.currency,
                    "source": line.source,
                    "fetchedAt": line.fetched_at,
                    "metadata": line.metadata or {},
                }
                for line in summary.provider_costs
            ],
            "costBreakdown": {
                "openaiRbycEur": float(summary.rbyc_raw),
                "veraOpenaiEur": float(summary.vera_openai_raw),
                "veraAnthropicEur": float(summary.vera_anthropic_raw),
                "veraTotalEur": float(summary.vera_raw),
                "rbycMarkupPercentage": float(summary.rbyc_markup_percentage),
                "veraMarkupPercentage": float(summary.vera_markup_percentage),
                "ivaPercentage": float(summary.vat_percentage),
            },
        }

    @staticmethod
    def charge_date_for_period(period_month: date) -> date:
        if period_month.month == 12:
            return date(period_month.year + 1, 1, 1)
        return date(period_month.year, period_month.month + 1, 1)

    @staticmethod
    def serialize_invoice(invoice: Optional[BillingInvoice]) -> Optional[dict]:
        if not invoice:
            return None
        return {
            "periodMonth": invoice.period_month.strftime("%Y-%m"),
            "amountEur": float(invoice.amount_eur),
            "currency": invoice.currency,
            "status": invoice.status,
            "paidAt": invoice.paid_at,
            "hostedInvoiceUrl": invoice.hosted_invoice_url,
            "invoicePdf": invoice.invoice_pdf,
            "lastError": invoice.last_error,
        }

    @staticmethod
    def current_period_month() -> date:
        today = timezone.localdate()
        return today.replace(day=1)

    @classmethod
    def refresh_vera_costs_for_month(cls, period_month: date):
        start_date = period_month.replace(day=1)
        end_date = min(cls.next_month(start_date) - timedelta(days=1), timezone.localdate())
        if end_date < start_date:
            return []
        return VeraCostSyncService.sync_range(start_date, end_date)

    @staticmethod
    def next_month(period_month: date) -> date:
        if period_month.month == 12:
            return date(period_month.year + 1, 1, 1)
        return date(period_month.year, period_month.month + 1, 1)

    @classmethod
    def _sum_vera_cost(cls, period_month: date, provider: str) -> Decimal:
        next_month = cls.next_month(period_month)
        total = (
            VeraUsageRecord.objects.filter(
                provider=provider,
                date__gte=period_month,
                date__lt=next_month,
            )
            .aggregate(total=Sum("cost_eur"))
            .get("total")
        )
        return cls._decimal(total)

    @staticmethod
    def _decimal(value) -> Decimal:
        return Decimal(str(value or "0")).quantize(INTERNAL_QUANT, ROUND_HALF_UP)

    @staticmethod
    def _apply_percentage(value: Decimal, percentage: Decimal) -> Decimal:
        return (value * (Decimal("1") + (percentage / Decimal("100")))).quantize(
            INTERNAL_QUANT,
            ROUND_HALF_UP,
        )

    @staticmethod
    def _join_errors(current: Optional[str], incoming: str) -> str:
        if current:
            return f"{current}; {incoming}"
        return incoming

    @staticmethod
    def currency() -> str:
        return getattr(settings, "BILLING_DEFAULT_CURRENCY", "EUR").upper()

    @staticmethod
    def rbyc_markup_percentage() -> Decimal:
        return Decimal(str(getattr(settings, "AI_USAGE_RBYC_MARKUP_PERCENTAGE", "20")))

    @staticmethod
    def vera_markup_percentage() -> Decimal:
        return Decimal(str(getattr(settings, "AI_USAGE_VERA_MARKUP_PERCENTAGE", "25")))

    @staticmethod
    def vat_percentage() -> Decimal:
        return Decimal(str(getattr(settings, "AI_USAGE_IVA_PERCENTAGE", "22")))
