from __future__ import annotations

import logging
from datetime import datetime, timezone as dt_timezone
from datetime import date
from typing import Any, Optional

from django.conf import settings
from django.db import transaction

from billing.models import BillingAccount, BillingInvoice, BillingInvoiceStatus
from billing.services.ai_usage_costs import AIUsageCostService

logger = logging.getLogger(__name__)


class StripeBillingService:
    @classmethod
    def build_status(cls) -> dict:
        account = BillingAccount.get_solo()
        latest_invoice = BillingInvoice.objects.order_by("-period_month").first()
        card = None
        if account.payment_method_ready:
            card = {
                "brand": account.card_brand,
                "last4": account.card_last4,
                "expMonth": account.card_exp_month,
                "expYear": account.card_exp_year,
            }

        return {
            "paymentMethodReady": account.payment_method_ready,
            "stripeCustomerReady": bool(account.stripe_customer_id),
            "card": card,
            "latestInvoice": cls._serialize_invoice(latest_invoice),
        }

    @classmethod
    def build_monthly_summary(cls, period_month: date) -> dict:
        return AIUsageCostService.serialize_for_billing(
            period_month,
            refresh_rbyc=False,
            refresh_vera=False,
        )

    @staticmethod
    def _charge_date_for_period(period_month: date) -> date:
        if period_month.month == 12:
            return date(period_month.year + 1, 1, 1)
        return date(period_month.year, period_month.month + 1, 1)

    @classmethod
    def create_setup_checkout_session(cls, *, user, request) -> dict:
        stripe = cls._stripe()
        account = BillingAccount.get_solo()
        customer_id = cls._ensure_customer(stripe, account, user=user)
        success_url = cls._frontend_url("/usage?billing=setup_success")
        cancel_url = cls._frontend_url("/usage?billing=setup_cancelled")

        session = stripe.checkout.Session.create(
            mode="setup",
            customer=customer_id,
            payment_method_types=["card"],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "billing_account_id": str(account.id),
                "user_id": str(getattr(user, "id", "")),
                "source": "rbyc_card_setup",
            },
        )
        return {"checkoutUrl": session.url, "sessionId": session.id}

    @classmethod
    def handle_webhook(cls, *, payload: bytes, signature: Optional[str]) -> dict:
        stripe = cls._stripe()
        webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)
        if not webhook_secret:
            raise RuntimeError("STRIPE_WEBHOOK_SECRET is not configured.")

        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature,
            secret=webhook_secret,
        )

        event_type = event["type"]
        obj = event["data"]["object"]
        logger.info("Received Stripe webhook", extra={"event_type": event_type})

        if event_type == "checkout.session.completed":
            cls._handle_checkout_session_completed(stripe, obj)
        elif event_type == "setup_intent.succeeded":
            cls._handle_setup_intent_succeeded(stripe, obj)
        elif event_type == "invoice.paid":
            cls._handle_invoice_paid(obj)
        elif event_type == "invoice.payment_failed":
            cls._handle_invoice_payment_failed(obj)
        elif event_type == "invoice.voided":
            cls._handle_invoice_status(obj, BillingInvoiceStatus.VOID)

        return {"received": True, "eventType": event_type}

    @classmethod
    def _ensure_customer(cls, stripe, account: BillingAccount, *, user) -> str:
        if account.stripe_customer_id:
            return account.stripe_customer_id

        customer_payload = {
            "metadata": {
                "billing_account_id": str(account.id),
                "created_from": "rbyc_app",
            },
        }
        if getattr(user, "email", None):
            customer_payload["email"] = user.email
        if user:
            customer_name = user.get_full_name() or getattr(user, "username", "")
            if customer_name:
                customer_payload["name"] = customer_name

        customer = stripe.Customer.create(**customer_payload)
        account.stripe_customer_id = customer.id
        account.save(update_fields=["stripe_customer_id", "updated_at"])
        return customer.id

    @classmethod
    def _handle_checkout_session_completed(cls, stripe, session) -> None:
        if cls._stripe_value(session, "mode") != "setup":
            return

        setup_intent_id = cls._stripe_value(session, "setup_intent")
        if not setup_intent_id:
            return

        setup_intent = stripe.SetupIntent.retrieve(setup_intent_id)
        cls._store_payment_method_from_setup_intent(stripe, setup_intent)

    @classmethod
    def _handle_setup_intent_succeeded(cls, stripe, setup_intent) -> None:
        cls._store_payment_method_from_setup_intent(stripe, setup_intent)

    @classmethod
    def _store_payment_method_from_setup_intent(cls, stripe, setup_intent) -> None:
        customer_id = cls._stripe_value(setup_intent, "customer")
        payment_method_id = cls._stripe_value(setup_intent, "payment_method")
        if not customer_id or not payment_method_id:
            return

        payment_method = stripe.PaymentMethod.retrieve(payment_method_id)
        card = cls._stripe_value(payment_method, "card", {}) or {}

        stripe.Customer.modify(
            customer_id,
            invoice_settings={"default_payment_method": payment_method_id},
        )

        with transaction.atomic():
            account = (
                BillingAccount.objects.select_for_update()
                .filter(stripe_customer_id=customer_id)
                .first()
            )
            if not account:
                account = BillingAccount.objects.select_for_update().order_by("id").first()
            if not account:
                account = BillingAccount.objects.create(stripe_customer_id=customer_id)
            account.stripe_customer_id = customer_id
            account.default_payment_method_id = payment_method_id
            account.card_brand = cls._stripe_value(card, "brand")
            account.card_last4 = cls._stripe_value(card, "last4")
            account.card_exp_month = cls._stripe_value(card, "exp_month")
            account.card_exp_year = cls._stripe_value(card, "exp_year")
            account.payment_method_ready = True
            account.save(
                update_fields=[
                    "default_payment_method_id",
                    "stripe_customer_id",
                    "card_brand",
                    "card_last4",
                    "card_exp_month",
                    "card_exp_year",
                    "payment_method_ready",
                    "updated_at",
                ]
            )

    @classmethod
    def _handle_invoice_paid(cls, stripe_invoice) -> None:
        invoice = cls._find_local_invoice(stripe_invoice)
        if not invoice:
            return

        paid_at = cls._stripe_value(stripe_invoice, "status_transitions", {}).get("paid_at")
        invoice.status = BillingInvoiceStatus.PAID
        if paid_at:
            invoice.paid_at = datetime.fromtimestamp(paid_at, tz=dt_timezone.utc)
        cls._copy_invoice_urls(invoice, stripe_invoice)
        invoice.last_error = None
        invoice.save(
            update_fields=[
                "status",
                "stripe_invoice_id",
                "paid_at",
                "hosted_invoice_url",
                "invoice_pdf",
                "stripe_payment_intent_id",
                "last_error",
                "updated_at",
            ]
        )

    @classmethod
    def _handle_invoice_payment_failed(cls, stripe_invoice) -> None:
        invoice = cls._find_local_invoice(stripe_invoice)
        if not invoice:
            return

        invoice.status = BillingInvoiceStatus.PAYMENT_FAILED
        cls._copy_invoice_urls(invoice, stripe_invoice)
        invoice.last_error = "Stripe invoice payment failed."
        invoice.save(
            update_fields=[
                "status",
                "stripe_invoice_id",
                "hosted_invoice_url",
                "invoice_pdf",
                "stripe_payment_intent_id",
                "last_error",
                "updated_at",
            ]
        )

    @classmethod
    def _handle_invoice_status(cls, stripe_invoice, status: str) -> None:
        invoice = cls._find_local_invoice(stripe_invoice)
        if not invoice:
            return
        invoice.status = status
        cls._copy_invoice_urls(invoice, stripe_invoice)
        invoice.save(
            update_fields=[
                "status",
                "stripe_invoice_id",
                "hosted_invoice_url",
                "invoice_pdf",
                "stripe_payment_intent_id",
                "updated_at",
            ]
        )

    @classmethod
    def _find_local_invoice(cls, stripe_invoice) -> Optional[BillingInvoice]:
        stripe_invoice_id = cls._stripe_value(stripe_invoice, "id")
        metadata = cls._stripe_value(stripe_invoice, "metadata", {}) or {}
        invoice_id = metadata.get("billing_invoice_id")
        period_month = metadata.get("period_month")

        if invoice_id:
            invoice = BillingInvoice.objects.filter(id=invoice_id).first()
            if invoice:
                return invoice

        if stripe_invoice_id:
            invoice = BillingInvoice.objects.filter(stripe_invoice_id=stripe_invoice_id).first()
            if invoice:
                return invoice

        if period_month:
            try:
                year_str, month_str = period_month.split("-", 1)
                period_date = date(int(year_str), int(month_str), 1)
            except (TypeError, ValueError):
                period_date = None
            if period_date:
                return BillingInvoice.objects.filter(period_month=period_date).first()
        return None

    @classmethod
    def _copy_invoice_urls(cls, invoice: BillingInvoice, stripe_invoice) -> None:
        invoice.stripe_invoice_id = cls._stripe_value(stripe_invoice, "id")
        invoice.stripe_payment_intent_id = cls._stripe_value(stripe_invoice, "payment_intent")
        invoice.hosted_invoice_url = cls._stripe_value(stripe_invoice, "hosted_invoice_url")
        invoice.invoice_pdf = cls._stripe_value(stripe_invoice, "invoice_pdf")

    @staticmethod
    def _serialize_invoice(invoice: Optional[BillingInvoice]) -> Optional[dict]:
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
    def _frontend_url(path: str) -> str:
        frontend_url = (getattr(settings, "FRONTEND_URL", "") or "").rstrip("/")
        if not frontend_url:
            raise RuntimeError("FRONTEND_URL is not configured.")
        return f"{frontend_url}{path}"

    @staticmethod
    def _stripe():
        secret_key = getattr(settings, "STRIPE_SECRET_KEY", None)
        if not secret_key:
            raise RuntimeError("STRIPE_SECRET_KEY is not configured.")

        import stripe

        stripe.api_key = secret_key
        return stripe

    @staticmethod
    def _stripe_value(obj: Any, key: str, default=None):
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
