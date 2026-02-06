from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from core.serializers.usage_serializers import (
    UsageManualRecordSerializer,
    UsageMonthOptionSerializer,
    UsageReportSerializer,
)
from core.services.usage_service import UsageReportFilters, UsageReportService
from core.services.usage_tracking import UsageTrackingService


def _parse_int(value: str, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError({field_name: "Deve essere un intero."}) from exc


def _build_filters(request) -> UsageReportFilters:
    month = request.query_params.get("month")
    company_param = request.query_params.get("companyId")
    user_param = request.query_params.get("userId")

    company_id = _parse_int(company_param, "companyId") if company_param else None
    user_id = _parse_int(user_param, "userId") if user_param else None

    return UsageReportFilters(month=month, company_id=company_id, user_id=user_id)


class UsageReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        filters = _build_filters(request)
        try:
            report = UsageReportService.build_report(filters)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        serializer = UsageReportSerializer(report)
        return Response(serializer.data)


class UsageMonthListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        filters = _build_filters(request)
        months = UsageReportService.list_available_months(filters)
        serializer = UsageMonthOptionSerializer(months, many=True)
        return Response(serializer.data)


class UsageManualRecordView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UsageManualRecordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        result = UsageTrackingService.record_usage_event(
            user=request.user,
            tool=data["tool"],
            sub_tool=data.get("subTool"),
            quantity=data.get("quantity"),
            metadata=data.get("metadata") or {},
            company=getattr(request.user, "company", None),
        )

        if result is None:
            return Response(
                {"detail": "Errore ao registrar consumo."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "status": "ok",
                "recordId": str(result.record.id),
                "unitPrice": float(result.unit_price),
                "totalCost": float(result.total_cost),
                "rateId": result.used_rate_id,
            },
            status=status.HTTP_201_CREATED,
        )
