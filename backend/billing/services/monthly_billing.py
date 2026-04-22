from __future__ import annotations

import calendar
import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Union

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from billing.models import BillingAccount, BillingInvoice, BillingInvoiceStatus
from billing.services.provider_costs import ProviderCostService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MonthlyBillingResult:
    invoice: BillingInvoice
    created: bool
    charged: bool
    total_usage_cost: Decimal


class MonthlyBillingService:
    @classmethod
    def generate_invoice_for_month(
        cls,
        month: Optional[Union[str, date]] = None,
        *,
        created_by_task: bool = False,
        created_by_user=None,
    ) -> MonthlyBillingResult:
        period_month = cls.normalize_month(month)
        provider_total = ProviderCostService.get_total_for_month(period_month)
        total_cost = provider_total.amount

        with transaction.atomic():
            invoice, created = BillingInvoice.objects.select_for_update().get_or_create(
                period_month=period_month,
                defaults={
                    "amount_eur": total_cost,
                    "currency": provider_total.currency,
                    "created_by_task": created_by_task,
                    "created_by_user": created_by_user,
                },
            )

            if invoice.status == BillingInvoiceStatus.PAID:
                return MonthlyBillingResult(
                    invoice=invoice,
                    created=created,
                    charged=False,
                    total_usage_cost=total_cost,
                )

            if invoice.stripe_invoice_id:
                synced_invoice = cls._sync_existing_stripe_invoice(invoice)
                return MonthlyBillingResult(
                    invoice=synced_invoice,
                    created=created,
                    charged=False,
                    total_usage_cost=total_cost,
                )

            if not created and invoice.attempt_count > 0:
                total_cost = invoice.amount_eur
                provider_total_currency = invoice.currency
            else:
                provider_total_currency = provider_total.currency

            invoice.amount_eur = total_cost
            invoice.currency = provider_total_currency
            invoice.created_by_task = invoice.created_by_task or created_by_task
            if created_by_user and not invoice.created_by_user_id:
                invoice.created_by_user = created_by_user

            invoice.mark_attempt()

            if total_cost <= Decimal("0"):
                invoice.status = BillingInvoiceStatus.NO_USAGE
                invoice.last_error = None
                invoice.save(
                    update_fields=[
                        "amount_eur",
                        "currency",
                        "created_by_task",
                        "created_by_user",
                        "attempt_count",
                        "last_attempt_at",
                        "status",
                        "last_error",
                        "updated_at",
                    ]
                )
                return MonthlyBillingResult(
                    invoice=invoice,
                    created=created,
                    charged=False,
                    total_usage_cost=total_cost,
                )

            invoice.status = BillingInvoiceStatus.CREATING
            invoice.last_error = None
            invoice.save(
                update_fields=[
                    "amount_eur",
                    "currency",
                    "created_by_task",
                    "created_by_user",
                    "attempt_count",
                    "last_attempt_at",
                    "status",
                    "last_error",
                    "updated_at",
                ]
            )

        try:
            stripe_invoice, stripe_invoice_item_id = cls._create_and_pay_stripe_invoice(invoice)
        except Exception as exc:
            logger.exception(
                "Error creating monthly Stripe invoice",
                extra={"period_month": period_month.strftime("%Y-%m")},
            )
            with transaction.atomic():
                invoice = BillingInvoice.objects.select_for_update().get(pk=invoice.pk)
                invoice.status = BillingInvoiceStatus.ERROR
                invoice.last_error = str(exc)
                invoice.save(update_fields=["status", "last_error", "updated_at"])
            raise

        with transaction.atomic():
            invoice = BillingInvoice.objects.select_for_update().get(pk=invoice.pk)
            cls._copy_stripe_invoice_fields(
                invoice,
                stripe_invoice,
                stripe_invoice_item_id=stripe_invoice_item_id,
            )
            if invoice.status == BillingInvoiceStatus.CREATING:
                invoice.status = BillingInvoiceStatus.OPEN
            invoice.save(
                update_fields=[
                    "status",
                    "stripe_invoice_id",
                    "stripe_invoice_item_id",
                    "stripe_payment_intent_id",
                    "hosted_invoice_url",
                    "invoice_pdf",
                    "paid_at",
                    "last_error",
                    "metadata",
                    "updated_at",
                ]
            )

        return MonthlyBillingResult(
            invoice=invoice,
            created=created,
            charged=True,
            total_usage_cost=total_cost,
        )

    @classmethod
    def normalize_month(cls, month: Optional[Union[str, date]]) -> date:
        if month is None:
            today = timezone.localdate()
            first_day = today.replace(day=1)
            if first_day.month == 1:
                return date(first_day.year - 1, 12, 1)
            return date(first_day.year, first_day.month - 1, 1)

        if isinstance(month, date):
            return month.replace(day=1)

        try:
            year_str, month_str = month.split("-", 1)
            return date(int(year_str), int(month_str), 1)
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError("Month must use YYYY-MM format.") from exc

    @staticmethod
    def currency() -> str:
        return getattr(settings, "BILLING_DEFAULT_CURRENCY", "EUR").upper()

    @staticmethod
    def idempotency_prefix() -> str:
        return getattr(settings, "BILLING_STRIPE_IDEMPOTENCY_PREFIX", "rbyc")

    @classmethod
    def _create_and_pay_stripe_invoice(cls, invoice: BillingInvoice):
        stripe = cls._stripe()
        account = BillingAccount.get_solo()
        cls._validate_account_for_charge(account)

        period_key = invoice.period_month.strftime("%Y-%m")
        idempotency_prefix = cls.idempotency_prefix()
        amount_cents = cls._eur_to_cents(invoice.amount_eur)
        description = cls._invoice_description(invoice.period_month)
        metadata = {
            "period_month": period_key,
            "source": "rbyc_monthly_usage",
        }

        invoice_item = stripe.InvoiceItem.create(
            customer=account.stripe_customer_id,
            amount=amount_cents,
            currency=invoice.currency.lower(),
            description=description,
            metadata=metadata,
            idempotency_key=f"{idempotency_prefix}-invoice-item-{period_key}",
        )

        stripe_invoice = stripe.Invoice.create(
            customer=account.stripe_customer_id,
            collection_method="charge_automatically",
            auto_advance=False,
            default_payment_method=account.default_payment_method_id,
            description=description,
            metadata=metadata,
            idempotency_key=f"{idempotency_prefix}-invoice-{period_key}",
        )

        finalized_invoice = stripe.Invoice.finalize_invoice(
            stripe_invoice.id,
            auto_advance=False,
            idempotency_key=f"{idempotency_prefix}-invoice-finalize-{period_key}",
        )

        if cls._stripe_value(finalized_invoice, "status") == "paid":
            return finalized_invoice, invoice_item.id

        try:
            paid_invoice = stripe.Invoice.pay(
                finalized_invoice.id,
                payment_method=account.default_payment_method_id,
                off_session=True,
                idempotency_key=f"{idempotency_prefix}-invoice-pay-{period_key}",
            )
        except Exception as exc:
            if "already paid" not in str(exc).lower():
                raise
            paid_invoice = stripe.Invoice.retrieve(finalized_invoice.id)

        return paid_invoice, invoice_item.id

    @classmethod
    def _sync_existing_stripe_invoice(cls, invoice: BillingInvoice) -> BillingInvoice:
        stripe = cls._stripe()
        stripe_invoice = stripe.Invoice.retrieve(invoice.stripe_invoice_id)
        cls._copy_stripe_invoice_fields(invoice, stripe_invoice)
        invoice.save(
            update_fields=[
                "status",
                "stripe_payment_intent_id",
                "hosted_invoice_url",
                "invoice_pdf",
                "paid_at",
                "last_error",
                "metadata",
                "updated_at",
            ]
        )
        return invoice

    @staticmethod
    def _stripe():
        secret_key = getattr(settings, "STRIPE_SECRET_KEY", None)
        if not secret_key:
            raise RuntimeError("STRIPE_SECRET_KEY is not configured.")

        import stripe

        stripe.api_key = secret_key
        return stripe

    @staticmethod
    def _validate_account_for_charge(account: BillingAccount) -> None:
        if not account.stripe_customer_id:
            raise RuntimeError("Stripe customer is not configured.")
        if not account.default_payment_method_id or not account.payment_method_ready:
            raise RuntimeError("Stripe payment method is not ready.")

    @staticmethod
    def _eur_to_cents(value: Decimal) -> int:
        return int((value * Decimal("100")).quantize(Decimal("1"), ROUND_HALF_UP))

    @staticmethod
    def _invoice_description(period_month: date) -> str:
        prefix = getattr(settings, "BILLING_INVOICE_DESCRIPTION_PREFIX", "RbyC AI usage")
        try:
            prefix = prefix.format(period_month=period_month)
        except (KeyError, ValueError):
            pass
        month_name = calendar.month_name[period_month.month]
        return f"{prefix} - {month_name} {period_month.year}"

    @classmethod
    def _copy_stripe_invoice_fields(
        cls,
        invoice: BillingInvoice,
        stripe_invoice,
        *,
        stripe_invoice_item_id: Optional[str] = None,
    ) -> None:
        status = cls._stripe_value(stripe_invoice, "status")
        if status == "paid":
            invoice.status = BillingInvoiceStatus.PAID
            paid_at = cls._stripe_value(stripe_invoice, "status_transitions", {}).get("paid_at")
            if paid_at:
                invoice.paid_at = datetime.fromtimestamp(paid_at, tz=dt_timezone.utc)
        elif status == "open":
            invoice.status = BillingInvoiceStatus.OPEN
        elif status == "void":
            invoice.status = BillingInvoiceStatus.VOID

        invoice.stripe_invoice_id = cls._stripe_value(stripe_invoice, "id")
        invoice.stripe_payment_intent_id = cls._stripe_value(stripe_invoice, "payment_intent")
        invoice.hosted_invoice_url = cls._stripe_value(stripe_invoice, "hosted_invoice_url")
        invoice.invoice_pdf = cls._stripe_value(stripe_invoice, "invoice_pdf")
        invoice.last_error = None
        invoice.metadata = {
            **(invoice.metadata or {}),
            "stripe_status": status,
            "stripe_invoice_item_id": stripe_invoice_item_id,
        }
        invoice.stripe_invoice_item_id = stripe_invoice_item_id

    @staticmethod
    def _stripe_value(obj, key: str, default=None):
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
