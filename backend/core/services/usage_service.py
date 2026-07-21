from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Iterable, Optional, Tuple

from django.contrib.auth import get_user_model
from django.db.models import Count, Max, QuerySet, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from billing.models import ProviderMonthlyCost
from core.models.usage import UsageRecord, UsageTool
from core.models.vera_usage_model import VeraUsageRecord
from integrations.models import IntegrationUsageRecord

UserModel = get_user_model()

MONTH_NAMES_IT = {
    1: "Gennaio",
    2: "Febbraio",
    3: "Marzo",
    4: "Aprile",
    5: "Maggio",
    6: "Giugno",
    7: "Luglio",
    8: "Agosto",
    9: "Settembre",
    10: "Ottobre",
    11: "Novembre",
    12: "Dicembre",
}


@dataclass
class UsageReportFilters:
    month: Optional[str] = None
    company_id: Optional[int] = None
    user_id: Optional[int] = None


def compute_month_bounds(month_str: Optional[str]) -> Tuple[date, datetime, datetime]:
    tz = timezone.get_current_timezone()
    if month_str:
        try:
            reference = datetime.strptime(month_str, "%Y-%m").date().replace(day=1)
        except ValueError as exc:  # pragma: no cover - validazione input
            raise ValueError("Formato del mese non valido. Use YYYY-MM.") from exc
    else:
        now = timezone.now().date()
        reference = now.replace(day=1)

    if reference.month == 12:
        next_month = date(reference.year + 1, 1, 1)
    else:
        next_month = date(reference.year, reference.month + 1, 1)

    start_dt = timezone.make_aware(datetime.combine(reference, time.min), tz)
    end_dt = timezone.make_aware(datetime.combine(next_month, time.min), tz)
    return reference, start_dt, end_dt


class UsageReportService:
    currency = "EUR"

    @classmethod
    def build_report(cls, filters: UsageReportFilters) -> Dict:
        month_ref, start_dt, end_dt = compute_month_bounds(filters.month)
        queryset = cls._apply_filters(UsageRecord.objects.all(), filters, start_dt, end_dt)
        integration_queryset = cls._apply_integration_filters(
            IntegrationUsageRecord.objects.select_related("client", "api_key"),
            filters,
            start_dt,
            end_dt,
        )

        totals = queryset.aggregate(total_qty=Sum("quantity", default=Decimal("0")))
        integration_total = integration_queryset.count()

        tool_usage = cls._aggregate_tool_usage(queryset, integration_queryset)
        user_breakdown = cls._aggregate_user_breakdown(queryset)
        integration_breakdown = cls._aggregate_integration_breakdown(
            integration_queryset
        )
        last_usage = cls._build_last_usage(queryset, integration_queryset)

        return {
            "month": month_ref.strftime("%Y-%m"),
            "monthLabel": f"{MONTH_NAMES_IT[month_ref.month]} {month_ref.year}",
            "currency": cls.currency,
            "totalRequests": cls._decimal_to_int(totals["total_qty"]) + integration_total,
            "lastUsage": last_usage,
            "toolUsage": tool_usage,
            "userBreakdown": user_breakdown,
            "integrationBreakdown": integration_breakdown,
        }

    @staticmethod
    def _apply_filters(
        queryset: QuerySet[UsageRecord],
        filters: UsageReportFilters,
        start_dt: datetime,
        end_dt: datetime,
    ) -> QuerySet[UsageRecord]:
        qs = queryset.filter(occurred_at__gte=start_dt, occurred_at__lt=end_dt)
        if filters.company_id:
            qs = qs.filter(company_id=filters.company_id)
        if filters.user_id:
            qs = qs.filter(user_id=filters.user_id)
        return qs

    @staticmethod
    def _apply_integration_filters(
        queryset,
        filters: UsageReportFilters,
        start_dt: datetime,
        end_dt: datetime,
    ):
        qs = queryset.filter(occurred_at__gte=start_dt, occurred_at__lt=end_dt)
        if filters.company_id or filters.user_id:
            return qs.none()
        return qs

    @classmethod
    def _aggregate_tool_usage(cls, queryset: QuerySet[UsageRecord], integration_queryset) -> Dict[str, Dict]:
        tool_rows = (
            queryset.values("tool", "sub_tool")
            .annotate(
                total_qty=Sum("quantity", default=Decimal("0")),
            )
        )

        totals: Dict[str, Dict] = {}
        for row in tool_rows:
            tool_key = row["tool"]
            sub_key = row["sub_tool"]
            tool_bucket = totals.setdefault(
                tool_key,
                {"count": Decimal("0"), "subItems": {}},
            )
            tool_bucket["count"] += row["total_qty"]

            if sub_key:
                tool_bucket["subItems"][sub_key] = {
                    "count": cls._decimal_to_int(row["total_qty"]),
                }

        integration_rows = (
            integration_queryset.values("tool")
            .annotate(total_qty=Count("id"))
        )
        for row in integration_rows:
            tool_key = row["tool"]
            tool_bucket = totals.setdefault(
                tool_key,
                {"count": Decimal("0"), "subItems": {}},
            )
            tool_bucket["count"] += cls._to_decimal(row["total_qty"], default=Decimal("0"))

        formatted: Dict[str, Dict] = {}
        for tool, data in totals.items():
            entry = {
                "count": cls._decimal_to_int(data["count"]),
            }
            if data["subItems"]:
                entry["subItems"] = data["subItems"]
            formatted[tool] = entry
        return formatted

    @classmethod
    def _aggregate_user_breakdown(cls, queryset: QuerySet[UsageRecord]) -> Iterable[Dict]:
        user_rows = (
            queryset.values("user", "tool", "sub_tool")
            .annotate(
                total_qty=Sum("quantity", default=Decimal("0")),
            )
        )
        def _decimal_dict():
            return defaultdict(lambda: Decimal("0"))

        user_buckets: Dict[int, Dict[str, Dict]] = defaultdict(
            lambda: {
                "counts": defaultdict(lambda: Decimal("0")),
                "sub_counts": defaultdict(_decimal_dict),
            }
        )

        user_ids = set()
        for row in user_rows:
            user_id = row["user"]
            user_ids.add(user_id)
            bucket = user_buckets[user_id]
            bucket["counts"][row["tool"]] += row["total_qty"]
            sub_tool_key = row["sub_tool"]
            if sub_tool_key:
                bucket["sub_counts"][row["tool"]][sub_tool_key] += row["total_qty"]

        users = {user.id: user for user in UserModel.objects.filter(id__in=user_ids)}

        tool_keys = [choice[0] for choice in UsageTool.choices]
        breakdown = []
        for user_id, aggregates in user_buckets.items():
            user = users.get(user_id)
            if not user:
                continue
            counts = {tool: 0 for tool in tool_keys}
            for tool, value in aggregates["counts"].items():
                counts[tool] = cls._decimal_to_int(value)
            total_count = sum(aggregates["counts"].values(), Decimal("0"))

            sub_tool_counts = {
                tool: {
                    sub_tool: cls._decimal_to_int(val)
                    for sub_tool, val in sub_dict.items()
                }
                for tool, sub_dict in aggregates["sub_counts"].items()
                if sub_dict
            }

            breakdown.append(
                {
                    "userId": user.id,
                    "userName": user.get_full_name() or user.email,
                    "userEmail": user.email,
                    "role": "Admin" if getattr(user, "is_company_admin", False) else "Utente",
                    "isCompanyAdmin": getattr(user, "is_company_admin", False),
                    "counts": counts,
                    "subToolCounts": sub_tool_counts,
                    "totalCount": cls._decimal_to_int(total_count),
                }
            )

        breakdown.sort(key=lambda item: item["totalCount"], reverse=True)
        return breakdown

    @classmethod
    def _aggregate_integration_breakdown(cls, queryset) -> Iterable[Dict]:
        records = list(queryset)
        client_buckets: Dict[str, Dict] = {}

        for record in records:
            client = getattr(record, "client", None)
            client_key = str(getattr(client, "id", None) or "legacy")
            client_bucket = client_buckets.setdefault(
                client_key,
                {
                    "clientId": getattr(client, "id", None),
                    "clientName": getattr(client, "client_name", None) or "Legacy integration",
                    "customerCode": getattr(client, "customer_code", None) or "",
                    "counts": defaultdict(int),
                    "totalCount": 0,
                    "apiKeysMap": {},
                },
            )

            documents_count = int(getattr(record, "documents_count", 0) or 0)
            tool = getattr(record, "tool", "") or ""
            client_bucket["counts"][tool] += 1
            client_bucket["totalCount"] += 1

            api_key = getattr(record, "api_key", None)
            api_key_id = getattr(api_key, "id", None)
            api_key_label = cls._normalize_integration_auth_label(
                getattr(record, "auth_identifier", "") or ""
            )
            api_key_key = str(api_key_id or api_key_label or f"auth-{record.id}")
            api_bucket = client_bucket["apiKeysMap"].setdefault(
                api_key_key,
                {
                    "apiKeyId": api_key_id,
                    "label": api_key_label,
                    "authMode": getattr(record, "auth_mode", "") or "",
                    "counts": defaultdict(int),
                    "totalCount": 0,
                    "documentsCount": 0,
                },
            )
            api_bucket["counts"][tool] += 1
            api_bucket["totalCount"] += 1
            api_bucket["documentsCount"] += documents_count

        formatted = []
        for bucket in client_buckets.values():
            api_keys = []
            for api_bucket in bucket["apiKeysMap"].values():
                api_keys.append(
                    {
                        "apiKeyId": api_bucket["apiKeyId"],
                        "label": api_bucket["label"],
                        "authMode": api_bucket["authMode"],
                        "counts": dict(api_bucket["counts"]),
                        "totalCount": api_bucket["totalCount"],
                    }
                )
            api_keys.sort(key=lambda item: item["totalCount"], reverse=True)
            formatted.append(
                {
                    "clientId": bucket["clientId"],
                    "clientName": bucket["clientName"],
                    "customerCode": bucket["customerCode"],
                    "counts": dict(bucket["counts"]),
                    "totalCount": bucket["totalCount"],
                    "apiKeys": api_keys,
                }
            )

        formatted.sort(key=lambda item: item["totalCount"], reverse=True)
        return formatted

    @classmethod
    def _build_last_usage(cls, queryset: QuerySet[UsageRecord], integration_queryset) -> Optional[Dict]:
        usage_latest = queryset.aggregate(value=Max("occurred_at")).get("value")
        integration_latest = integration_queryset.aggregate(value=Max("occurred_at")).get("value")
        latest_values = [value for value in [usage_latest, integration_latest] if value]
        if not latest_values:
            return None

        latest = max(latest_values)
        local_latest = timezone.localtime(latest)
        day_start = local_latest.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        usage_total = queryset.filter(
            occurred_at__gte=day_start,
            occurred_at__lt=day_end,
        ).aggregate(total=Sum("quantity", default=Decimal("0"))).get("total")
        integration_total = integration_queryset.filter(
            occurred_at__gte=day_start,
            occurred_at__lt=day_end,
        ).count()

        return {
            "occurredAt": latest,
            "date": local_latest.date().isoformat(),
            "totalRequests": cls._decimal_to_int(usage_total) + integration_total,
        }

    @classmethod
    def list_available_months(cls, filters: UsageReportFilters) -> Iterable[Dict]:
        queryset = UsageRecord.objects.all()
        if filters.company_id:
            queryset = queryset.filter(company_id=filters.company_id)
        if filters.user_id:
            queryset = queryset.filter(user_id=filters.user_id)

        months = list(
            queryset.annotate(month=TruncMonth("occurred_at"))
            .values("month")
            .distinct()
            .order_by("-month")
        )

        if not filters.company_id and not filters.user_id:
            integration_months = list(
                IntegrationUsageRecord.objects.annotate(month=TruncMonth("occurred_at"))
                .values("month")
                .distinct()
                .order_by("-month")
            )
            months.extend(integration_months)

            provider_cost_months = list(
                ProviderMonthlyCost.objects.annotate(month=TruncMonth("period_month"))
                .values("month")
                .distinct()
                .order_by("-month")
            )
            vera_cost_months = list(
                VeraUsageRecord.objects.annotate(month=TruncMonth("date"))
                .values("month")
                .distinct()
                .order_by("-month")
            )
            months.extend(provider_cost_months)
            months.extend(vera_cost_months)

        current_month = timezone.localdate().replace(day=1)
        months.append({"month": current_month})

        results = []
        seen = set()
        for entry in months:
            month_value = entry["month"]
            if not month_value:
                continue
            if isinstance(month_value, datetime):
                month_date = month_value.date()
            else:
                month_date = month_value
            month_key = month_date.strftime("%Y-%m")
            if month_key in seen:
                continue
            seen.add(month_key)
            label = f"{MONTH_NAMES_IT[month_date.month]} {month_date.year}"
            results.append(
                {
                    "value": month_key,
                    "label": label,
                }
            )
        results.sort(key=lambda item: item["value"], reverse=True)
        return results

    @staticmethod
    def _money_to_float(value: Optional[Decimal]) -> float:
        quantized = (value or Decimal("0")).quantize(Decimal("0.01"), ROUND_HALF_UP)
        return float(quantized)

    @staticmethod
    def _decimal_to_int(value: Optional[Decimal]) -> int:
        if value is None:
            return 0
        return int(value.to_integral_value(rounding=ROUND_HALF_UP))

    @staticmethod
    def _to_decimal(value, default: Optional[Decimal] = None) -> Decimal:
        if value is None:
            return default or Decimal("0")
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    @staticmethod
    def _normalize_integration_auth_label(value: str) -> str:
        label = (value or "").strip()
        if not label:
            return ""
        if label.lower().startswith("hash:"):
            return ""
        return label
