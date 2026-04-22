# Generated manually for provider request-level billing separation.

from decimal import Decimal

import django.db.models.deletion
from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0018_remove_usage_pricing"),
        ("billing", "0003_alter_providermonthlycost_currency"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProviderUsageCost",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(choices=[("openai", "OpenAI"), ("gemini", "Gemini"), ("perplexity", "Perplexity")], max_length=32)),
                ("external_request_id", models.CharField(blank=True, max_length=255, null=True)),
                ("occurred_at", models.DateTimeField(db_index=True, default=timezone.now)),
                ("amount", models.DecimalField(decimal_places=4, default=Decimal("0.0000"), max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal("0"))])),
                ("currency", models.CharField(default="EUR", max_length=3)),
                ("provider_currency", models.CharField(blank=True, max_length=3, null=True)),
                ("raw_payload", models.JSONField(blank=True, default=dict)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("usage_record", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="provider_usage_costs", to="core.usagerecord")),
            ],
            options={
                "verbose_name": "Provider usage cost",
                "verbose_name_plural": "Provider usage costs",
                "ordering": ["-occurred_at", "provider"],
            },
        ),
        migrations.AddIndex(
            model_name="providerusagecost",
            index=models.Index(fields=["provider", "occurred_at"], name="provider_usage_cost_date_idx"),
        ),
        migrations.AddConstraint(
            model_name="providerusagecost",
            constraint=models.UniqueConstraint(condition=models.Q(("external_request_id__isnull", False)), fields=("provider", "external_request_id"), name="uniq_provider_usage_cost_request"),
        ),
    ]