from __future__ import annotations

import secrets
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional

from django.conf import settings
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework import permissions
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models.usage import UsageRecord, UsageTool, UsageSubTool
from core.services.usage_service import compute_month_bounds


@dataclass(frozen=True)
class PeriodWindow:
    start: datetime
    end: datetime


class CostAggregatorAPIKeyAuthentication(BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        api_key = getattr(settings, "COST_AGGREGATOR_API_KEY", None)
        if not api_key:
            raise AuthenticationFailed("API key is not configured.")

        header = request.headers.get("Authorization")
        if not header:
            raise AuthenticationFailed("Missing Authorization header.")

        try:
            scheme, token = header.split(" ", 1)
        except ValueError as exc:
            raise AuthenticationFailed("Invalid Authorization header format.") from exc

        if scheme != self.keyword:
            raise AuthenticationFailed("Invalid authorization scheme.")

        if not secrets.compare_digest(token.strip(), api_key):
            raise AuthenticationFailed("Invalid API key.")

        # No associated Django user is required for this integration
        return (None, None)


class CostAggregatorView(APIView):
    authentication_classes = [CostAggregatorAPIKeyAuthentication]
    permission_classes = [permissions.AllowAny]

    project_id_setting = "COST_AGGREGATOR_PROJECT_ID"
    project_name_setting = "COST_AGGREGATOR_PROJECT_NAME"
    currency_setting = "COST_AGGREGATOR_DEFAULT_CURRENCY"

    def get(self, request, *args, **kwargs):
        period = self._resolve_period(request)
        queryset = UsageRecord.objects.filter(
            occurred_at__gte=period.start,
            occurred_at__lt=period.end,
        )

        totals = queryset.aggregate(total_cost=Sum("total_cost_eur", default=Decimal("0")))
        items = self._build_items(queryset)
        monthly_breakdown = self._build_monthly_breakdown(queryset)

        response_payload = {
            "projectId": getattr(settings, self.project_id_setting),
            "projectName": getattr(settings, self.project_name_setting),
            "currency": getattr(settings, self.currency_setting, "EUR"),
            "period": {
                "start": self._format_iso(period.start),
                "end": self._format_iso(period.end),
            },
            "totalCost": self._money_to_float(totals.get("total_cost")),
            "items": items,
            "monthlyBreakdown": monthly_breakdown,
        }

        return Response(response_payload)

    def _resolve_period(self, request) -> PeriodWindow:
        start_param = request.query_params.get("start")
        end_param = request.query_params.get("end")
        month_param = request.query_params.get("month")

        if start_param or end_param:
            if not start_param or not end_param:
                raise ValidationError({"period": "Both 'start' and 'end' must be provided."})

            start_dt = self._parse_iso_datetime(start_param, "start")
            end_dt = self._parse_iso_datetime(end_param, "end")

            if start_dt >= end_dt:
                raise ValidationError({"period": "'start' must be earlier than 'end'."})

            return PeriodWindow(start=start_dt, end=end_dt)

        try:
            _, start_dt, end_dt = compute_month_bounds(month_param)
        except ValueError as exc:
            raise ValidationError({"month": str(exc)}) from exc

        return PeriodWindow(start=start_dt, end=end_dt)

    @staticmethod
    def _parse_iso_datetime(value: str, field_name: str) -> datetime:
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValidationError({field_name: "Use ISO 8601 format."}) from exc

        if parsed.tzinfo is None:
            parsed = timezone.make_aware(parsed, dt_timezone.utc)
        else:
            parsed = parsed.astimezone(dt_timezone.utc)
        return parsed

    def _build_items(self, queryset) -> list[Dict]:
        tool_labels = dict(UsageTool.choices)
        sub_tool_labels = dict(UsageSubTool.choices)
        currency = getattr(settings, self.currency_setting, "EUR")

        aggregation = queryset.values("tool", "sub_tool").annotate(
            amount=Sum("total_cost_eur")
        )

        buckets: Dict[str, Dict] = {}
        for entry in aggregation:
            tool_code = entry.get("tool")
            sub_tool_code = entry.get("sub_tool")
            amount = entry.get("amount") or Decimal("0")

            tool_bucket = buckets.setdefault(
                tool_code,
                {
                    "label": tool_labels.get(tool_code, tool_code or "Unknown"),
                    "amount": Decimal("0"),
                    "subItems": defaultdict(lambda: Decimal("0")),
                },
            )
            tool_bucket["amount"] += amount
            if sub_tool_code:
                tool_bucket["subItems"][sub_tool_code] += amount

        items = []
        for tool_code, data in sorted(buckets.items(), key=lambda item: item[1]["label"]):
            metadata: Dict[str, Optional[list]] = {"toolCode": tool_code}
            sub_items_meta = []
            for sub_tool_code, sub_amount in sorted(data["subItems"].items()):
                sub_items_meta.append(
                    {
                        "code": sub_tool_code,
                        "label": sub_tool_labels.get(sub_tool_code, sub_tool_code or ""),
                        "amount": self._money_to_float(sub_amount),
                    }
                )
            if sub_items_meta:
                metadata["subItems"] = sub_items_meta

            items.append(
                {
                    "label": data["label"],
                    "amount": self._money_to_float(data["amount"]),
                    "currency": currency,
                    "metadata": metadata,
                }
            )

        return items

    def _build_monthly_breakdown(self, queryset) -> list[Dict]:
        monthly_rows = (
            queryset.annotate(month=TruncMonth("occurred_at"))
            .values("month")
            .annotate(total_cost=Sum("total_cost_eur", default=Decimal("0")))
            .order_by("month")
        )

        breakdown = []
        for row in monthly_rows:
            month_value = row.get("month")
            if not month_value:
                continue
            if isinstance(month_value, datetime):
                month_date = month_value.date()
            else:
                month_date = month_value
            breakdown.append(
                {
                    "month": month_date.strftime("%Y-%m"),
                    "totalCost": self._money_to_float(row.get("total_cost")),
                }
            )
        return breakdown

    @staticmethod
    def _money_to_float(value: Optional[Decimal]) -> float:
        quantized = (value or Decimal("0")).quantize(Decimal("0.01"), ROUND_HALF_UP)
        return float(quantized)

    @staticmethod
    def _format_iso(value: datetime) -> str:
        return (
            value.astimezone(dt_timezone.utc)
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z")
        )
