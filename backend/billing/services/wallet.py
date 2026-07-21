from __future__ import annotations

from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from billing.models import (
    BillingAccount,
    Wallet,
    WalletTransaction,
    WalletTransactionStatus,
    WalletTransactionType,
)
from billing.services.stripe_billing import StripeBillingService


class WalletService:
    @classmethod
    def build_status(cls) -> dict:
        wallet = Wallet.get_solo()
        account = wallet.billing_account
        card = None
        if account.payment_method_ready:
            card = {
                "brand": account.card_brand,
                "last4": account.card_last4,
                "expMonth": account.card_exp_month,
                "expYear": account.card_exp_year,
            }

        return {
            "balanceEur": float(wallet.balance_eur),
            "currency": wallet.currency,
            "autoRechargeEnabled": wallet.auto_recharge_enabled,
            "rechargeAmountEur": float(wallet.recharge_amount_eur),
            "thresholdEur": float(wallet.threshold_eur),
            "paymentMethodReady": account.payment_method_ready,
            "stripeCustomerReady": bool(account.stripe_customer_id),
            "card": card,
            "lastError": wallet.last_error,
            "needsRecharge": wallet.balance_eur <= wallet.threshold_eur,
        }

    @classmethod
    def list_transactions(cls, *, limit: int = 100) -> list[WalletTransaction]:
        limit = max(1, min(limit, 200))
        wallet = Wallet.get_solo()
        return list(wallet.transactions.all()[:limit])

    @classmethod
    def credit(
        cls,
        *,
        amount_eur: Decimal,
        description: str,
        transaction_type: str = WalletTransactionType.CREDIT,
        idempotency_key: Optional[str] = None,
        stripe_payment_intent_id: Optional[str] = None,
        created_by_user=None,
        metadata: Optional[dict] = None,
    ) -> WalletTransaction:
        amount_eur = cls._money(amount_eur)
        if amount_eur <= Decimal("0.00"):
            raise ValueError("Credit amount must be greater than zero.")

        with transaction.atomic():
            if idempotency_key:
                existing = WalletTransaction.objects.select_for_update().filter(
                    idempotency_key=idempotency_key
                ).first()
                if existing:
                    return existing

            wallet = Wallet.objects.select_for_update().get(pk=Wallet.get_solo().pk)
            wallet.balance_eur = cls._money(wallet.balance_eur + amount_eur)
            wallet.last_error = None
            wallet.save(update_fields=["balance_eur", "last_error", "updated_at"])
            return WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type=transaction_type,
                status=WalletTransactionStatus.COMPLETED,
                amount_eur=amount_eur,
                balance_after_eur=wallet.balance_eur,
                description=description,
                idempotency_key=idempotency_key,
                stripe_payment_intent_id=stripe_payment_intent_id,
                created_by_user=created_by_user,
                metadata=metadata or {},
            )

    @classmethod
    def debit_usage(
        cls,
        *,
        amount_eur: Decimal,
        description: str,
        idempotency_key: str,
        period_start=None,
        period_end=None,
        metadata: Optional[dict] = None,
    ) -> WalletTransaction:
        amount_eur = cls._money(amount_eur)
        if amount_eur <= Decimal("0.00"):
            raise ValueError("Debit amount must be greater than zero.")

        with transaction.atomic():
            existing = WalletTransaction.objects.select_for_update().filter(
                idempotency_key=idempotency_key
            ).first()
            if existing:
                return existing

            wallet = Wallet.objects.select_for_update().get(pk=Wallet.get_solo().pk)
            wallet.balance_eur = cls._money(wallet.balance_eur - amount_eur)
            wallet.save(update_fields=["balance_eur", "updated_at"])
            return WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type=WalletTransactionType.USAGE_DEBIT,
                status=WalletTransactionStatus.COMPLETED,
                amount_eur=-amount_eur,
                balance_after_eur=wallet.balance_eur,
                description=description,
                idempotency_key=idempotency_key,
                period_start=period_start,
                period_end=period_end,
                metadata=metadata or {},
            )

    @classmethod
    def create_admin_adjustment(
        cls,
        *,
        amount_eur: Decimal,
        description: str,
        created_by_user=None,
    ) -> WalletTransaction:
        amount_eur = cls._money(amount_eur)
        if amount_eur == Decimal("0.00"):
            raise ValueError("Adjustment amount cannot be zero.")

        if amount_eur > 0:
            return cls.credit(
                amount_eur=amount_eur,
                description=description,
                transaction_type=WalletTransactionType.ADMIN_ADJUSTMENT,
                created_by_user=created_by_user,
            )
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(pk=Wallet.get_solo().pk)
            wallet.balance_eur = cls._money(wallet.balance_eur + amount_eur)
            wallet.save(update_fields=["balance_eur", "updated_at"])
            return WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type=WalletTransactionType.ADMIN_ADJUSTMENT,
                status=WalletTransactionStatus.COMPLETED,
                amount_eur=amount_eur,
                balance_after_eur=wallet.balance_eur,
                description=description,
                idempotency_key=f"admin-adjustment:{timezone.now().timestamp()}",
                created_by_user=created_by_user,
                metadata={"source": "admin_adjustment"},
            )

    @classmethod
    def recharge(cls, *, user=None, automatic: bool = False) -> WalletTransaction:
        wallet = Wallet.get_solo()
        if automatic and not wallet.auto_recharge_enabled:
            raise ValueError("Auto recharge is disabled.")
        if automatic and wallet.balance_eur > wallet.threshold_eur:
            raise ValueError("Wallet balance is above the recharge threshold.")

        account = BillingAccount.get_solo()
        if not account.payment_method_ready or not account.default_payment_method_id:
            return cls._record_payment_failure(
                wallet=wallet,
                description="Wallet recharge failed: no payment method registered.",
                automatic=automatic,
                error="No payment method registered.",
                user=user,
            )

        amount_eur = cls._money(wallet.recharge_amount_eur)
        transaction_type = (
            WalletTransactionType.AUTO_RECHARGE
            if automatic
            else WalletTransactionType.MANUAL_RECHARGE
        )
        idempotency_key = cls._recharge_idempotency_key(wallet=wallet, automatic=automatic)

        existing = WalletTransaction.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing

        stripe = StripeBillingService._stripe()
        wallet.last_recharge_attempt_at = timezone.now()
        wallet.save(update_fields=["last_recharge_attempt_at", "updated_at"])

        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=cls._eur_to_cents(amount_eur),
                currency="eur",
                customer=account.stripe_customer_id,
                payment_method=account.default_payment_method_id,
                confirm=True,
                off_session=True,
                description="RbyC wallet recharge",
                metadata={
                    "source": "rbyc_wallet_recharge",
                    "wallet_id": str(wallet.id),
                    "automatic": str(automatic).lower(),
                },
                idempotency_key=f"{getattr(settings, 'BILLING_STRIPE_IDEMPOTENCY_PREFIX', 'rbyc')}-wallet-{idempotency_key}",
            )
        except Exception as exc:
            return cls._record_payment_failure(
                wallet=wallet,
                description="Wallet recharge failed.",
                automatic=automatic,
                error=str(exc),
                user=user,
                idempotency_key=f"{idempotency_key}:failed",
            )

        if StripeBillingService._stripe_value(payment_intent, "status") != "succeeded":
            return cls._record_payment_failure(
                wallet=wallet,
                description="Wallet recharge did not complete.",
                automatic=automatic,
                error=f"Stripe status: {StripeBillingService._stripe_value(payment_intent, 'status')}",
                user=user,
                idempotency_key=f"{idempotency_key}:failed",
                stripe_payment_intent_id=StripeBillingService._stripe_value(payment_intent, "id"),
            )

        return cls.credit(
            amount_eur=amount_eur,
            description="Ricarica automatica wallet" if automatic else "Ricarica wallet",
            transaction_type=transaction_type,
            idempotency_key=idempotency_key,
            stripe_payment_intent_id=StripeBillingService._stripe_value(payment_intent, "id"),
            created_by_user=user,
            metadata={"automatic": automatic},
        )

    @classmethod
    def maybe_auto_recharge(cls) -> Optional[WalletTransaction]:
        wallet = Wallet.get_solo()
        if not wallet.auto_recharge_enabled or wallet.balance_eur > wallet.threshold_eur:
            return None
        return cls.recharge(automatic=True)

    @classmethod
    def debit_ai_usage_for_month(cls, period_month=None) -> dict:
        from billing.services.ai_usage_costs import AIUsageCostService

        period_month = (period_month or AIUsageCostService.current_period_month()).replace(day=1)
        summary = AIUsageCostService.build_monthly_summary(
            period_month,
            refresh_rbyc=False,
            refresh_vera=False,
        )
        target_total = cls._money(summary.total_with_vat)
        already_debited = cls._already_debited_for_month(period_month)
        delta = cls._money(target_total - already_debited)

        result = {
            "period_month": period_month.strftime("%Y-%m"),
            "target_total_eur": str(target_total),
            "already_debited_eur": str(already_debited),
            "delta_eur": str(delta),
            "debit_transaction_id": None,
            "recharge_transaction_id": None,
            "status": "no_delta",
        }

        if delta <= Decimal("0.00"):
            return result

        transaction = cls.debit_usage(
            amount_eur=delta,
            description=f"Consumo AI {period_month:%Y-%m}",
            idempotency_key=f"ai-usage-debit:{period_month:%Y-%m}:{target_total}",
            period_start=period_month,
            period_end=AIUsageCostService.next_month(period_month) - timedelta(days=1),
            metadata={
                "source": "ai_usage_monthly_summary",
                "target_total_eur": str(target_total),
                "already_debited_eur": str(already_debited),
                "rbyc_raw": str(summary.rbyc_raw),
                "vera_raw": str(summary.vera_raw),
                "total_with_vat": str(summary.total_with_vat),
            },
        )
        result["debit_transaction_id"] = transaction.id
        result["status"] = "debited"

        recharge_transaction = cls.maybe_auto_recharge()
        if recharge_transaction:
            result["recharge_transaction_id"] = recharge_transaction.id
            if recharge_transaction.status == WalletTransactionStatus.FAILED:
                result["status"] = "debited_recharge_failed"
            else:
                result["status"] = "debited_recharged"

        return result

    @classmethod
    def _already_debited_for_month(cls, period_month) -> Decimal:
        wallet = Wallet.get_solo()
        total = (
            WalletTransaction.objects.filter(
                wallet=wallet,
                transaction_type=WalletTransactionType.USAGE_DEBIT,
                status=WalletTransactionStatus.COMPLETED,
                period_start=period_month,
            )
            .aggregate(total=Sum("amount_eur"))
            .get("total")
        )
        return abs(cls._money(total or Decimal("0.00")))

    @classmethod
    def _record_payment_failure(
        cls,
        *,
        wallet: Wallet,
        description: str,
        automatic: bool,
        error: str,
        user=None,
        idempotency_key: Optional[str] = None,
        stripe_payment_intent_id: Optional[str] = None,
    ) -> WalletTransaction:
        wallet.last_error = error
        wallet.save(update_fields=["last_error", "updated_at"])
        return WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=WalletTransactionType.PAYMENT_FAILED,
            status=WalletTransactionStatus.FAILED,
            amount_eur=Decimal("0.00"),
            balance_after_eur=wallet.balance_eur,
            description=description,
            idempotency_key=idempotency_key,
            stripe_payment_intent_id=stripe_payment_intent_id,
            created_by_user=user,
            metadata={"automatic": automatic, "error": error},
        )

    @staticmethod
    def _money(value: Decimal) -> Decimal:
        return Decimal(str(value)).quantize(Decimal("0.01"), ROUND_HALF_UP)

    @staticmethod
    def _eur_to_cents(value: Decimal) -> int:
        return int((value * Decimal("100")).quantize(Decimal("1"), ROUND_HALF_UP))

    @staticmethod
    def _recharge_idempotency_key(*, wallet: Wallet, automatic: bool) -> str:
        prefix = "auto" if automatic else "manual"
        minute_key = timezone.now().strftime("%Y%m%d%H%M")
        return f"wallet-recharge:{wallet.id}:{prefix}:{minute_key}"
