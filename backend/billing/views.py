from __future__ import annotations

import secrets

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.serializers import (
    BillingMonthlySummarySerializer,
    BillingSetupSessionSerializer,
    BillingStatusSerializer,
    WalletAdminAdjustmentInputSerializer,
    WalletRechargeSerializer,
    WalletStatusSerializer,
    WalletTransactionSerializer,
)
from billing.services.internal_costs import (
    InternalCostsConfigurationError,
    InternalCostsSettings,
    build_internal_costs_payload,
)
from billing.services.monthly_billing import MonthlyBillingService
from billing.services.stripe_billing import StripeBillingService
from billing.services.wallet import WalletService


class IsCompanyAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, "is_company_admin", False)
                or getattr(request.user, "is_staff", False)
                or getattr(request.user, "is_superuser", False)
            )
        )


class BillingStatusView(APIView):
    permission_classes = [IsCompanyAdmin]

    def get(self, request, *args, **kwargs):
        payload = StripeBillingService.build_status()
        serializer = BillingStatusSerializer(payload)
        return Response(serializer.data)


class BillingMonthlySummaryView(APIView):
    permission_classes = [IsCompanyAdmin]

    def get(self, request, *args, **kwargs):
        try:
            period_month = MonthlyBillingService.normalize_month(
                request.query_params.get("month")
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        payload = StripeBillingService.build_monthly_summary(period_month)
        serializer = BillingMonthlySummarySerializer(payload)
        return Response(serializer.data)


class BillingSetupSessionView(APIView):
    permission_classes = [IsCompanyAdmin]

    def post(self, request, *args, **kwargs):
        payload = StripeBillingService.create_setup_checkout_session(
            user=request.user,
            request=request,
        )
        serializer = BillingSetupSessionSerializer(payload)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class WalletStatusView(APIView):
    permission_classes = [IsCompanyAdmin]

    def get(self, request, *args, **kwargs):
        serializer = WalletStatusSerializer(WalletService.build_status())
        return Response(serializer.data)


class WalletTransactionListView(APIView):
    permission_classes = [IsCompanyAdmin]

    def get(self, request, *args, **kwargs):
        try:
            limit = int(request.query_params.get("limit", "100"))
            offset = int(request.query_params.get("offset", "0"))
        except ValueError:
            return Response({"detail": "Invalid pagination parameters."}, status=status.HTTP_400_BAD_REQUEST)
        limit = max(1, min(limit, 200))
        offset = max(0, offset)
        serializer = WalletTransactionSerializer(
            WalletService.list_transactions(limit=limit, offset=offset),
            many=True,
        )
        count = WalletService.count_transactions()
        return Response(
            {
                "count": count,
                "limit": limit,
                "offset": offset,
                "results": serializer.data,
            }
        )


class WalletRechargeView(APIView):
    permission_classes = [IsCompanyAdmin]

    def post(self, request, *args, **kwargs):
        transaction = WalletService.recharge(user=request.user, automatic=False)
        payload = {
            "transaction": transaction,
            "wallet": WalletService.build_status(),
        }
        serializer = WalletRechargeSerializer(payload)
        status_code = (
            status.HTTP_402_PAYMENT_REQUIRED
            if transaction.status == "failed"
            else status.HTTP_201_CREATED
        )
        return Response(serializer.data, status=status_code)


class WalletAdminAdjustmentView(APIView):
    permission_classes = [IsCompanyAdmin]

    def post(self, request, *args, **kwargs):
        if not request.user.is_staff and not request.user.is_superuser:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        input_serializer = WalletAdminAdjustmentInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        try:
            transaction = WalletService.create_admin_adjustment(
                amount_eur=input_serializer.validated_data["amountEur"],
                description=input_serializer.validated_data["description"],
                created_by_user=request.user,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = WalletTransactionSerializer(transaction)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class InternalCostsView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        try:
            internal_settings = InternalCostsSettings.from_settings()
        except InternalCostsConfigurationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        auth_header = request.headers.get("Authorization", "")
        expected_header = f"Bearer {internal_settings.token}"
        if not auth_header or not secrets.compare_digest(auth_header, expected_header):
            return Response({"detail": "Unauthorized."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            payload = build_internal_costs_payload(request.query_params.get("month"))
        except ValueError as exc:
            raise ValidationError({"month": str(exc)}) from exc
        except InternalCostsConfigurationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(payload)


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        signature = request.headers.get("Stripe-Signature")
        try:
            payload = StripeBillingService.handle_webhook(
                payload=request.body,
                signature=signature,
            )
        except ValueError:
            return Response({"detail": "Invalid Stripe webhook payload."}, status=400)
        except Exception as exc:
            if exc.__class__.__name__ == "SignatureVerificationError":
                return Response({"detail": "Invalid Stripe webhook signature."}, status=400)
            raise
        return Response(payload)
