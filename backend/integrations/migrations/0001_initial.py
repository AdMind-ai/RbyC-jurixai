from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import hashlib
import django.utils.timezone


def bootstrap_global_integration_key(apps, schema_editor):
    integration_key = getattr(settings, "INTEGRATION_API_KEY", None)
    bucket_name = getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
    if not integration_key or not bucket_name:
        return

    IntegrationClient = apps.get_model("integrations", "IntegrationClient")
    IntegrationApiKey = apps.get_model("integrations", "IntegrationApiKey")

    client, _ = IntegrationClient.objects.update_or_create(
        customer_code="default",
        defaults={
            "client_name": "Default integration client",
            "bucket_name": bucket_name,
            "active": True,
            "sync_status": "idle",
            "sync_error": "",
        },
    )
    key_hash = hashlib.sha256(integration_key.encode("utf-8")).hexdigest()
    IntegrationApiKey.objects.update_or_create(
        key_hash=key_hash,
        defaults={
            "client": client,
            "active": True,
            "description": "Bootstrap from INTEGRATION_API_KEY",
            "environment": "current",
        },
    )


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="IntegrationClient",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("customer_code", models.CharField(max_length=128, unique=True)),
                ("client_name", models.CharField(max_length=255)),
                ("bucket_name", models.CharField(max_length=255)),
                ("active", models.BooleanField(default=True)),
                ("last_sync_at", models.DateTimeField(blank=True, null=True)),
                ("sync_status", models.CharField(default="idle", max_length=32)),
                ("sync_error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="IntegrationApiKey",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key_hash", models.CharField(max_length=64, unique=True)),
                ("active", models.BooleanField(default=True)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("environment", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "client",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="api_keys", to="integrations.integrationclient"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="DocumentIndex",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("bucket_name", models.CharField(max_length=255)),
                ("object_key", models.TextField()),
                ("filename", models.CharField(max_length=512)),
                ("extension", models.CharField(blank=True, max_length=32)),
                ("size_bytes", models.BigIntegerField(default=0)),
                ("last_modified", models.DateTimeField(blank=True, null=True)),
                ("etag", models.CharField(blank=True, max_length=128)),
                ("year", models.CharField(blank=True, max_length=4)),
                ("document_type", models.CharField(default="altro", max_length=64)),
                ("text_preview", models.TextField(blank=True)),
                ("extracted_text", models.TextField(blank=True)),
                (
                    "extraction_status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("ready", "Ready"),
                            ("failed", "Failed"),
                            ("skipped", "Skipped"),
                        ],
                        default="pending",
                        max_length=32,
                    ),
                ),
                ("extraction_error", models.TextField(blank=True)),
                ("active", models.BooleanField(default=True)),
                ("indexed_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "client",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="documents", to="integrations.integrationclient"),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="integrationclient",
            index=models.Index(fields=["active", "customer_code"], name="integratio_active_8183c6_idx"),
        ),
        migrations.AddIndex(
            model_name="integrationclient",
            index=models.Index(fields=["bucket_name"], name="integratio_bucket__a0e6ce_idx"),
        ),
        migrations.AddIndex(
            model_name="integrationapikey",
            index=models.Index(fields=["active", "key_hash"], name="integratio_active_f8f624_idx"),
        ),
        migrations.AddIndex(
            model_name="integrationapikey",
            index=models.Index(fields=["client", "active"], name="integratio_client__97a794_idx"),
        ),
        migrations.AddIndex(
            model_name="documentindex",
            index=models.Index(fields=["client", "active", "document_type"], name="integratio_client__c0a241_idx"),
        ),
        migrations.AddIndex(
            model_name="documentindex",
            index=models.Index(fields=["client", "active", "year"], name="integratio_client__5d6c56_idx"),
        ),
        migrations.AddIndex(
            model_name="documentindex",
            index=models.Index(fields=["client", "active", "last_modified"], name="integratio_client__355574_idx"),
        ),
        migrations.AddIndex(
            model_name="documentindex",
            index=models.Index(fields=["bucket_name"], name="integratio_bucket__fe0305_idx"),
        ),
        migrations.AddConstraint(
            model_name="documentindex",
            constraint=models.UniqueConstraint(fields=("client", "object_key"), name="unique_document_index_client_object_key"),
        ),
        migrations.RunPython(bootstrap_global_integration_key, migrations.RunPython.noop),
    ]
