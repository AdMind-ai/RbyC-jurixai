# Generated manually for the Stripe monthly billing foundation.

from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="BillingAccount",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "stripe_customer_id",
                    models.CharField(blank=True, max_length=255, null=True, unique=True),
                ),
                (
                    "default_payment_method_id",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("card_brand", models.CharField(blank=True, max_length=64, null=True)),
                ("card_last4", models.CharField(blank=True, max_length=4, null=True)),
                ("card_exp_month", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("card_exp_year", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("payment_method_ready", models.BooleanField(default=False)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Billing account",
                "verbose_name_plural": "Billing accounts",
            },
        ),
        migrations.CreateModel(
            name="BillingInvoice",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("period_month", models.DateField(unique=True)),
                (
                    "amount_eur",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(Decimal("0"))],
                    ),
                ),
                ("currency", models.CharField(default="EUR", max_length=3)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("creating", "Creating"),
                            ("open", "Open"),
                            ("paid", "Paid"),
                            ("payment_failed", "Payment failed"),
                            ("no_usage", "No usage"),
                            ("void", "Void"),
                            ("error", "Error"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=32,
                    ),
                ),
                (
                    "stripe_invoice_id",
                    models.CharField(blank=True, max_length=255, null=True, unique=True),
                ),
                (
                    "stripe_invoice_item_id",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "stripe_payment_intent_id",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("hosted_invoice_url", models.URLField(blank=True, max_length=1000, null=True)),
                ("invoice_pdf", models.URLField(blank=True, max_length=1000, null=True)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True, null=True)),
                ("attempt_count", models.PositiveIntegerField(default=0)),
                ("last_attempt_at", models.DateTimeField(blank=True, null=True)),
                ("created_by_task", models.BooleanField(default=False)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_billing_invoices",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Billing invoice",
                "verbose_name_plural": "Billing invoices",
                "ordering": ["-period_month"],
            },
        ),
    ]
