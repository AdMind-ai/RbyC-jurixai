# Generated manually for provider-level monthly costs.

from decimal import Decimal

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProviderMonthlyCost",
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
                    "provider",
                    models.CharField(
                        choices=[
                            ("openai", "OpenAI"),
                            ("gemini", "Gemini"),
                            ("perplexity", "Perplexity"),
                        ],
                        max_length=32,
                    ),
                ),
                ("period_month", models.DateField()),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=4,
                        default=Decimal("0.0000"),
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(Decimal("0"))],
                    ),
                ),
                (
                    "provider_amount",
                    models.DecimalField(
                        decimal_places=4,
                        default=Decimal("0.0000"),
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(Decimal("0"))],
                    ),
                ),
                (
                    "markup_percentage",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("20.00"),
                        max_digits=5,
                        validators=[django.core.validators.MinValueValidator(Decimal("0"))],
                    ),
                ),
                (
                    "amount_with_markup",
                    models.DecimalField(
                        decimal_places=4,
                        default=Decimal("0.0000"),
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(Decimal("0"))],
                    ),
                ),
                (
                    "vat_percentage",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("22.00"),
                        max_digits=5,
                        validators=[django.core.validators.MinValueValidator(Decimal("0"))],
                    ),
                ),
                (
                    "total_with_vat",
                    models.DecimalField(
                        decimal_places=4,
                        default=Decimal("0.0000"),
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(Decimal("0"))],
                    ),
                ),
                ("currency", models.CharField(default="EUR", max_length=3)),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("actual_api", "Actual API"),
                            ("billing_export", "Billing export"),
                            ("estimated", "Estimated"),
                            ("manual", "Manual"),
                            ("not_configured", "Not configured"),
                        ],
                        default="not_configured",
                        max_length=32,
                    ),
                ),
                ("external_project_id", models.CharField(blank=True, max_length=255, null=True)),
                ("fetched_at", models.DateTimeField(blank=True, null=True)),
                ("raw_payload", models.JSONField(blank=True, default=dict)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Provider monthly cost",
                "verbose_name_plural": "Provider monthly costs",
                "ordering": ["-period_month", "provider"],
            },
        ),
        migrations.AddConstraint(
            model_name="providermonthlycost",
            constraint=models.UniqueConstraint(
                fields=("provider", "period_month"),
                name="uniq_provider_monthly_cost",
            ),
        ),
    ]
