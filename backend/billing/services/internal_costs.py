from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone as dt_timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from django.conf import settings
from django.utils import timezone

from billing.models import ProviderMonthlyCost, ProviderUsageCost
from billing.services.aws_costs import AwsCostExplorerService
from billing.services.fx_rates import EuropeanCentralBankFxService, FxQuote, FxRateLookupError

TARGET_CURRENCY = "EUR"


class InternalCostsConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class CostCollectionResult:
    items: list[dict]
    total: Decimal
    status: str
    errors: list[dict]


@dataclass(frozen=True)
class InternalCostsSettings:
    project_id: str
    project_name: str
    token: str
    currency: str

    @classmethod
    def from_settings(cls) -> "InternalCostsSettings":
        return cls(
            project_id=cls._required("INTERNAL_COSTS_PROJECT_ID"),
            project_name=cls._required("INTERNAL_COSTS_PROJECT_NAME"),
            token=cls._required("INTERNAL_COSTS_TOKEN"),
            currency=TARGET_CURRENCY,
        )

    @staticmethod
    def _required(name: str) -> str:
        value = getattr(settings, name, None)
        if value is None or str(value).strip() == "":
            raise InternalCostsConfigurationError(f"{name} is not configured.")
        return str(value).strip()


def normalize_month(month_value: Optional[str]) -> date:
    if not month_value:
        now_utc = timezone.now().astimezone(dt_timezone.utc)
        return date(now_utc.year, now_utc.month, 1)

    try:
        parsed = datetime.strptime(month_value, "%Y-%m").date()
    except ValueError as exc:
        raise ValueError("Month must use YYYY-MM format.") from exc
    return parsed.replace(day=1)


def collect_ai_costs(*, period_month: date, currency: str) -> CostCollectionResult:
    period_key = period_month.strftime("%Y-%m")
    start_dt, end_dt = month_bounds_utc(period_month)
    items: list[dict] = []
    total = Decimal("0.00")

    usage_costs = (
        ProviderUsageCost.objects.select_related("usage_record")
        .filter(occurred_at__gte=start_dt, occurred_at__lt=end_dt)
        .order_by("provider", "occurred_at", "id")
    )

    grouped_usage: dict[tuple[str, str, str], dict] = {}
    for cost in usage_costs:
        provider = (cost.provider or "unknown").lower()
        service = _resolve_ai_service(cost)
        label = _resolve_ai_label(provider, service)
        key = (provider, service, cost.currency.upper())
        bucket = grouped_usage.setdefault(
            key,
            {
                "category": "ai",
                "provider": provider,
                "service": service,
                "label": label,
                "amount": Decimal("0.00"),
                "currency": cost.currency.upper(),
                "periodMonth": period_key,
                "metadata": {
                    "source": "provider_usage_costs",
                },
            },
        )
        bucket["amount"] += Decimal(str(cost.amount))

    for bucket in grouped_usage.values():
        bucket["amount"] = float(
            Decimal(str(bucket["amount"])).quantize(Decimal("0.01"), ROUND_HALF_UP)
        )
        total += Decimal(str(bucket["amount"]))
        items.append(bucket)

    if items:
        return CostCollectionResult(
            items=items,
            total=total.quantize(Decimal("0.01"), ROUND_HALF_UP),
            status="ok",
            errors=[],
        )

    monthly_costs = list(
        ProviderMonthlyCost.objects.filter(period_month=period_month).order_by("provider")
    )
    for monthly_cost in monthly_costs:
        provider = (monthly_cost.provider or "unknown").lower()
        amount = Decimal(str(monthly_cost.provider_amount or monthly_cost.amount or Decimal("0")))
        if amount == Decimal("0"):
            continue

        item = {
            "category": "ai",
            "provider": provider,
            "service": provider,
            "label": _resolve_ai_label(provider, provider),
            "amount": float(amount.quantize(Decimal("0.01"), ROUND_HALF_UP)),
            "currency": (monthly_cost.currency or currency).upper(),
            "periodMonth": period_key,
            "metadata": {
                "source": monthly_cost.source,
                "billingBasis": "provider_monthly_cost",
            },
        }
        items.append(item)
        total += Decimal(str(item["amount"]))

    if items:
        return CostCollectionResult(
            items=items,
            total=total.quantize(Decimal("0.01"), ROUND_HALF_UP),
            status="ok",
            errors=[],
        )

    # TODO: integrate direct provider billing APIs here for providers without persisted usage rows.
    return CostCollectionResult(items=[], total=Decimal("0.00"), status="ok", errors=[])


def build_internal_costs_payload(month_value: Optional[str]) -> dict:
    config = InternalCostsSettings.from_settings()
    period_month = normalize_month(month_value)
    period_start, period_end = month_bounds_utc(period_month)

    ai_result = _collect_with_fallback(
        scope="ai",
        collector=lambda: collect_ai_costs(period_month=period_month, currency=config.currency),
    )
    infra_result = _collect_with_fallback(
        scope="infra",
        collector=lambda: _collect_aws_costs(period_month=period_month, currency=config.currency),
    )

    ai_items = _normalize_items_currency(items=ai_result.items, target_currency=config.currency)
    infra_items = _normalize_items_currency(items=infra_result.items, target_currency=config.currency)

    ai_total = _sum_item_amounts(ai_items).quantize(Decimal("0.01"), ROUND_HALF_UP)
    infra_total = _sum_item_amounts(infra_items).quantize(Decimal("0.01"), ROUND_HALF_UP)
    overall_total = (ai_total + infra_total).quantize(Decimal("0.01"), ROUND_HALF_UP)
    overall_status = _merge_status(ai_result.status, infra_result.status)

    return {
        "version": "v1",
        "projectId": config.project_id,
        "projectName": config.project_name,
        "currency": config.currency,
        "generatedAt": isoformat_utc(timezone.now()),
        "period": {
            "start": isoformat_utc(period_start),
            "end": isoformat_utc(period_end),
            "month": period_month.strftime("%Y-%m"),
        },
        "totals": {
            "ai": _money_to_float(ai_total),
            "infra": _money_to_float(infra_total),
            "total": _money_to_float(overall_total),
        },
        "monthlyBreakdown": [
            {
                "month": period_month.strftime("%Y-%m"),
                "ai": _money_to_float(ai_total),
                "infra": _money_to_float(infra_total),
                "total": _money_to_float(overall_total),
                "currency": config.currency,
            }
        ],
        "items": [*ai_items, *infra_items],
        "status": {
            "overall": overall_status,
            "ai": ai_result.status,
            "infra": infra_result.status,
        },
        "errors": [*ai_result.errors, *infra_result.errors],
    }


def month_bounds_utc(period_month: date) -> tuple[datetime, datetime]:
    start = datetime.combine(period_month, time.min, tzinfo=dt_timezone.utc)
    if period_month.month == 12:
        next_month = date(period_month.year + 1, 1, 1)
    else:
        next_month = date(period_month.year, period_month.month + 1, 1)
    end = datetime.combine(next_month, time.min, tzinfo=dt_timezone.utc)
    return start, end


def isoformat_utc(value: datetime) -> str:
    return value.astimezone(dt_timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _collect_aws_costs(*, period_month: date, currency: str) -> CostCollectionResult:
    result = AwsCostExplorerService.collect_monthly_costs(period_month=period_month, currency=currency)
    return CostCollectionResult(
        items=result.items,
        total=result.total,
        status="ok",
        errors=[],
    )


def _collect_with_fallback(*, scope: str, collector) -> CostCollectionResult:
    try:
        return collector()
    except Exception as exc:
        return CostCollectionResult(
            items=[],
            total=Decimal("0.00"),
            status="error",
            errors=[
                {
                    "scope": scope,
                    "code": _error_code(scope, exc),
                    "message": str(exc),
                }
            ],
        )


def _merge_status(ai_status: str, infra_status: str) -> str:
    statuses = {ai_status, infra_status}
    if statuses == {"ok"}:
        return "ok"
    if "ok" in statuses:
        return "partial"
    if "error" in statuses and len(statuses) == 1:
        return "error"
    return "partial"


def _resolve_ai_service(cost: ProviderUsageCost) -> str:
    metadata = cost.metadata or {}
    usage_record = getattr(cost, "usage_record", None)

    for key in ("service", "model", "provider_model", "model_name"):
        value = metadata.get(key)
        if value:
            return str(value).lower()

    if usage_record and getattr(usage_record, "sub_tool", None):
        return str(usage_record.sub_tool).lower()

    return str(cost.provider or "unknown").lower()


def _resolve_ai_label(provider: str, service: str) -> str:
    if provider == "openai":
        return "OpenAI API"
    if provider == "perplexity":
        return "Perplexity API"
    provider_label = provider.upper() if len(provider) <= 4 else provider.capitalize()
    if service and service != provider:
        return f"{provider_label} {service}"
    return f"{provider_label} API"


def _error_code(scope: str, exc: Exception) -> str:
    slug = exc.__class__.__name__.replace("_", "-").lower()
    return f"{scope}_{slug}"


def _normalize_items_currency(*, target_currency: str, items: list[dict]) -> list[dict]:
    normalized_items: list[dict] = []
    for item in items:
        normalized_items.append(_normalize_item_currency(item=item, target_currency=target_currency))
    return normalized_items


def _normalize_item_currency(*, item: dict, target_currency: str) -> dict:
    source_currency = str(item.get("currency") or target_currency).upper()
    amount = Decimal(str(item.get("amount") or "0"))
    normalized_item = {
        **item,
        "metadata": {**(item.get("metadata") or {})},
    }

    if source_currency == target_currency:
        normalized_item["amount"] = _money_to_float(amount)
        normalized_item["currency"] = target_currency
        return normalized_item

    quote = _get_fx_quote(base_currency=source_currency, quote_currency=target_currency)
    converted_amount = (amount * quote.rate).quantize(Decimal("0.01"), ROUND_HALF_UP)
    normalized_item["amount"] = _money_to_float(converted_amount)
    normalized_item["currency"] = target_currency
    normalized_item["metadata"].update(
        {
            "originalAmount": _money_to_float(amount),
            "originalCurrency": source_currency,
            "fxRate": float(quote.rate),
            "fxDate": quote.fx_date,
            "fxSource": quote.source,
        }
    )
    return normalized_item


def _get_fx_quote(*, base_currency: str, quote_currency: str):
    override_rate = getattr(settings, "INTERNAL_COSTS_USD_TO_EUR_RATE", None)
    override_date = getattr(settings, "INTERNAL_COSTS_FX_DATE", None)
    if (
        base_currency.upper() == "USD"
        and quote_currency.upper() == "EUR"
        and override_rate not in (None, "")
    ):
        return FxQuote(
            base_currency="USD",
            quote_currency="EUR",
            rate=Decimal(str(override_rate)),
            fx_date=str(override_date or timezone.now().date().isoformat()),
            source="settings_override",
        )

    try:
        return EuropeanCentralBankFxService.get_quote(
            base_currency=base_currency,
            quote_currency=quote_currency,
        )
    except FxRateLookupError as exc:
        raise InternalCostsConfigurationError(str(exc)) from exc


def _sum_item_amounts(items: list[dict]) -> Decimal:
    total = Decimal("0.00")
    for item in items:
        total += Decimal(str(item.get("amount") or "0"))
    return total


def _money_to_float(value: Decimal) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), ROUND_HALF_UP))
