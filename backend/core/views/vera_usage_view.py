import logging
from datetime import date, timedelta

from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models.vera_usage_model import VeraUsageRecord
from core.serializers.vera_usage_serializer import (
    VeraUsageIngestSerializer,
    VeraUsageRecordSerializer,
)

logger = logging.getLogger(__name__)

# Numero di giorni restituiti di default dal chart endpoint
DEFAULT_DAYS = 30


class VeraUsageIngestView(APIView):
    """
    POST /api/vera/usage/
    Riceve un singolo record di consumo da OpenAI o Anthropic.
    Esegue upsert su (date, provider, model).
    Endpoint protetto: solo staff o service account.
    """
    # Per chiamate machine-to-machine basta IsAuthenticated;
    # in produzione si può restringere a IsAdminUser o token specifico.
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = VeraUsageIngestSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning("VeraUsage ingest error: %s", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        record = serializer.save()
        return Response(VeraUsageRecordSerializer(record).data, status=status.HTTP_201_CREATED)


class VeraUsageDailyView(APIView):
    """
    GET /api/vera/usage/daily/?days=30&provider=openai
    Restituisce i dati aggregati giornalieri per il grafico frontend.

    Response shape:
    {
      "days": 30,
      "series": [
        {
          "date": "2026-07-01",
          "openai_tokens": 12500,
          "anthropic_tokens": 8300,
          "openai_cost_eur": 0.12,
          "anthropic_cost_eur": 0.09,
          "openai_requests": 5,
          "anthropic_requests": 3,
          "total_tokens": 20800,
          "total_cost_eur": 0.21,
        },
        ...
      ]
    }
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            days = int(request.query_params.get("days", DEFAULT_DAYS))
            days = max(1, min(days, 365))
        except (ValueError, TypeError):
            days = DEFAULT_DAYS

        since = date.today() - timedelta(days=days - 1)

        # Raw queryset: un record per (date, provider, model)
        qs = (
            VeraUsageRecord.objects
            .filter(date__gte=since)
            .values("date", "provider")
            .annotate(
                tokens=Sum("total_tokens"),
                inputs=Sum("input_tokens"),
                outputs=Sum("output_tokens"),
                requests=Sum("request_count"),
                cost=Sum("cost_eur"),
            )
            .order_by("date", "provider")
        )

        # Pivot in Python: costruisce una entry per ogni data
        pivot: dict[str, dict] = {}
        for row in qs:
            d = row["date"].isoformat()
            if d not in pivot:
                pivot[d] = {
                    "date": d,
                    "openai_tokens": 0,
                    "anthropic_tokens": 0,
                    "openai_cost_eur": None,
                    "anthropic_cost_eur": None,
                    "openai_requests": 0,
                    "anthropic_requests": 0,
                }
            p = row["provider"]
            pivot[d][f"{p}_tokens"]   = row["tokens"] or 0
            pivot[d][f"{p}_requests"] = row["requests"] or 0
            if row["cost"] is not None:
                pivot[d][f"{p}_cost_eur"] = float(row["cost"])

        # Riempi i giorni senza dati con zeri (così il grafico non ha buchi)
        all_days = []
        for i in range(days):
            d = (since + timedelta(days=i)).isoformat()
            entry = pivot.get(d, {
                "date": d,
                "openai_tokens": 0,
                "anthropic_tokens": 0,
                "openai_cost_eur": None,
                "anthropic_cost_eur": None,
                "openai_requests": 0,
                "anthropic_requests": 0,
            })
            # Totali
            entry["total_tokens"]   = entry["openai_tokens"] + entry["anthropic_tokens"]
            oa = entry.get("openai_cost_eur")
            an = entry.get("anthropic_cost_eur")
            if oa is not None or an is not None:
                entry["total_cost_eur"] = (oa or 0) + (an or 0)
            else:
                entry["total_cost_eur"] = None
            all_days.append(entry)

        return Response({"days": days, "series": all_days})


class VeraUsageRawListView(APIView):
    """
    GET /api/vera/usage/raw/   — lista record grezzi (ultimi 500, solo admin)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        qs = VeraUsageRecord.objects.all()[:500]
        return Response(VeraUsageRecordSerializer(qs, many=True).data)
