from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Iterable, Optional, Tuple

from django.contrib.auth import get_user_model
from django.db.models import QuerySet, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from core.models.usage import UsageRecord, UsageTool

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


class UsageReportService:
    currency = "EUR"

    @classmethod
    def build_report(cls, filters: UsageReportFilters) -> Dict:
        month_ref, start_dt, end_dt = cls._compute_month_bounds(filters.month)
        queryset = cls._apply_filters(UsageRecord.objects.all(), filters, start_dt, end_dt)

        totals = queryset.aggregate(
            total_cost=Sum("total_cost_eur", default=Decimal("0")),
            total_qty=Sum("quantity", default=Decimal("0")),
        )

        tool_usage = cls._aggregate_tool_usage(queryset)
        user_breakdown = cls._aggregate_user_breakdown(queryset)

        return {
            "month": month_ref.strftime("%Y-%m"),
            "monthLabel": f"{MONTH_NAMES_IT[month_ref.month]} {month_ref.year}",
            "currency": cls.currency,
            "totalCost": cls._money_to_float(totals["total_cost"]),
            "totalRequests": cls._decimal_to_int(totals["total_qty"]),
            "toolUsage": tool_usage,
            "userBreakdown": user_breakdown,
        }

    @staticmethod
    def _compute_month_bounds(month_str: Optional[str]) -> Tuple[date, datetime, datetime]:
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

    @classmethod
    def _aggregate_tool_usage(cls, queryset: QuerySet[UsageRecord]) -> Dict[str, Dict]:
        tool_rows = (
            queryset.values("tool", "sub_tool")
            .annotate(
                total_cost=Sum("total_cost_eur", default=Decimal("0")),
                total_qty=Sum("quantity", default=Decimal("0")),
            )
        )

        totals: Dict[str, Dict] = {}
        for row in tool_rows:
            tool_key = row["tool"]
            sub_key = row["sub_tool"]
            tool_bucket = totals.setdefault(
                tool_key,
                {"cost": Decimal("0"), "count": Decimal("0"), "subItems": {}},
            )
            tool_bucket["cost"] += row["total_cost"]
            tool_bucket["count"] += row["total_qty"]

            if sub_key:
                tool_bucket["subItems"][sub_key] = {
                    "cost": cls._money_to_float(row["total_cost"]),
                    "count": cls._decimal_to_int(row["total_qty"]),
                }

        formatted: Dict[str, Dict] = {}
        for tool, data in totals.items():
            entry = {
                "cost": cls._money_to_float(data["cost"]),
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
                total_cost=Sum("total_cost_eur", default=Decimal("0")),
                total_qty=Sum("quantity", default=Decimal("0")),
            )
        )
        def _decimal_dict():
            return defaultdict(lambda: Decimal("0"))

        user_buckets: Dict[int, Dict[str, Dict]] = defaultdict(
            lambda: {
                "costs": defaultdict(lambda: Decimal("0")),
                "counts": defaultdict(lambda: Decimal("0")),
                "sub_costs": defaultdict(_decimal_dict),
                "sub_counts": defaultdict(_decimal_dict),
            }
        )

        user_ids = set()
        for row in user_rows:
            user_id = row["user"]
            user_ids.add(user_id)
            bucket = user_buckets[user_id]
            bucket["costs"][row["tool"]] += row["total_cost"]
            bucket["counts"][row["tool"]] += row["total_qty"]
            sub_tool_key = row["sub_tool"]
            if sub_tool_key:
                bucket["sub_costs"][row["tool"]][sub_tool_key] += row["total_cost"]
                bucket["sub_counts"][row["tool"]][sub_tool_key] += row["total_qty"]

        users = {user.id: user for user in UserModel.objects.filter(id__in=user_ids)}

        tool_keys = [choice[0] for choice in UsageTool.choices]
        breakdown = []
        for user_id, aggregates in user_buckets.items():
            user = users.get(user_id)
            if not user:
                continue
            costs = {tool: 0.0 for tool in tool_keys}
            counts = {tool: 0 for tool in tool_keys}
            for tool, value in aggregates["costs"].items():
                costs[tool] = cls._money_to_float(value)
            for tool, value in aggregates["counts"].items():
                counts[tool] = cls._decimal_to_int(value)
            total_cost_decimal = sum(aggregates["costs"].values(), Decimal("0"))

            sub_tool_costs = {
                tool: {
                    sub_tool: cls._money_to_float(val)
                    for sub_tool, val in sub_dict.items()
                }
                for tool, sub_dict in aggregates["sub_costs"].items()
                if sub_dict
            }

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
                    "costs": costs,
                    "counts": counts,
                    "subToolCosts": sub_tool_costs,
                    "subToolCounts": sub_tool_counts,
                    "totalCost": cls._money_to_float(total_cost_decimal),
                }
            )

        breakdown.sort(key=lambda item: item["totalCost"], reverse=True)
        return breakdown

    @classmethod
    def list_available_months(cls, filters: UsageReportFilters) -> Iterable[Dict]:
        queryset = UsageRecord.objects.all()
        if filters.company_id:
            queryset = queryset.filter(company_id=filters.company_id)
        if filters.user_id:
            queryset = queryset.filter(user_id=filters.user_id)

        months = (
            queryset.annotate(month=TruncMonth("occurred_at"))
            .values("month")
            .annotate(total_cost=Sum("total_cost_eur", default=Decimal("0")))
            .order_by("-month")
        )

        results = []
        for entry in months:
            month_value = entry["month"]
            if not month_value:
                continue
            if isinstance(month_value, datetime):
                month_date = month_value.date()
            else:
                month_date = month_value
            label = f"{MONTH_NAMES_IT[month_date.month]} {month_date.year}"
            results.append(
                {
                    "value": month_date.strftime("%Y-%m"),
                    "label": label,
                    "totalCost": cls._money_to_float(entry["total_cost"]),
                }
            )
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
