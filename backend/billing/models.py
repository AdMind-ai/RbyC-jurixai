from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class BillingInvoiceStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CREATING = "creating", "Creating"
    OPEN = "open", "Open"
    PAID = "paid", "Paid"
    PAYMENT_FAILED = "payment_failed", "Payment failed"
    NO_USAGE = "no_usage", "No usage"
    VOID = "void", "Void"
    ERROR = "error", "Error"


class ProviderCostProvider(models.TextChoices):
    OPENAI = "openai", "OpenAI"
    GEMINI = "gemini", "Gemini"
    PERPLEXITY = "perplexity", "Perplexity"


class ProviderCostSource(models.TextChoices):
    ACTUAL_API = "actual_api", "Actual API"
    BILLING_EXPORT = "billing_export", "Billing export"
    ESTIMATED = "estimated", "Estimated"
    MANUAL = "manual", "Manual"
    NOT_CONFIGURED = "not_configured", "Not configured"


class BillingAccount(models.Model):
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    default_payment_method_id = models.CharField(max_length=255, blank=True, null=True)
    card_brand = models.CharField(max_length=64, blank=True, null=True)
    card_last4 = models.CharField(max_length=4, blank=True, null=True)
    card_exp_month = models.PositiveSmallIntegerField(blank=True, null=True)
    card_exp_year = models.PositiveSmallIntegerField(blank=True, null=True)
    payment_method_ready = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Billing account"
        verbose_name_plural = "Billing accounts"

    def __str__(self) -> str:
        return self.stripe_customer_id or "Billing account"

    @classmethod
    def get_solo(cls) -> "BillingAccount":
        account = cls.objects.order_by("id").first()
        if account:
            return account
        return cls.objects.create()


class BillingInvoice(models.Model):
    period_month = models.DateField(unique=True)
    amount_eur = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    currency = models.CharField(max_length=3, default="EUR")
    status = models.CharField(
        max_length=32,
        choices=BillingInvoiceStatus.choices,
        default=BillingInvoiceStatus.PENDING,
        db_index=True,
    )
    stripe_invoice_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    stripe_invoice_item_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    hosted_invoice_url = models.URLField(max_length=1000, blank=True, null=True)
    invoice_pdf = models.URLField(max_length=1000, blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    last_error = models.TextField(blank=True, null=True)
    attempt_count = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(blank=True, null=True)
    created_by_task = models.BooleanField(default=False)
    created_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="created_billing_invoices",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Billing invoice"
        verbose_name_plural = "Billing invoices"
        ordering = ["-period_month"]

    def __str__(self) -> str:
        return f"{self.period_month:%Y-%m} - {self.amount_eur} {self.currency} - {self.status}"

    def mark_attempt(self) -> None:
        self.attempt_count += 1
        self.last_attempt_at = timezone.now()


class ProviderMonthlyCost(models.Model):
    provider = models.CharField(max_length=32, choices=ProviderCostProvider.choices)
    period_month = models.DateField()
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal("0.0000"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    provider_amount = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal("0.0000"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    markup_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("20.00"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    amount_with_markup = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal("0.0000"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    vat_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("22.00"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    total_with_vat = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal("0.0000"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    currency = models.CharField(max_length=3, default="USD")
    source = models.CharField(
        max_length=32,
        choices=ProviderCostSource.choices,
        default=ProviderCostSource.NOT_CONFIGURED,
    )
    external_project_id = models.CharField(max_length=255, blank=True, null=True)
    fetched_at = models.DateTimeField(blank=True, null=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Provider monthly cost"
        verbose_name_plural = "Provider monthly costs"
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "period_month"],
                name="uniq_provider_monthly_cost",
            )
        ]
        ordering = ["-period_month", "provider"]

    def __str__(self) -> str:
        return f"{self.provider} - {self.period_month:%Y-%m} - {self.amount} {self.currency}"
