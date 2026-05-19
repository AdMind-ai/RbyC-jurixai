from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("integrations", "0010_documentindex_search_text"),
    ]

    operations = [
        migrations.CreateModel(
            name="IntegrationUsageRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tool", models.CharField(choices=[("RICERCA_DOCUMENTALE", "Ricerca documentale")], default="RICERCA_DOCUMENTALE", max_length=64)),
                ("request_id", models.CharField(blank=True, db_index=True, max_length=64)),
                ("conversation_id", models.CharField(blank=True, max_length=255)),
                ("auth_mode", models.CharField(blank=True, max_length=64)),
                ("auth_identifier", models.CharField(blank=True, max_length=255)),
                ("intent_type", models.CharField(blank=True, max_length=128)),
                ("prompt_length", models.PositiveIntegerField(default=0)),
                ("model_input_length", models.PositiveIntegerField(default=0)),
                ("response_text_length", models.PositiveIntegerField(default=0)),
                ("documents_count", models.PositiveIntegerField(default=0)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("occurred_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("api_key", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="usage_records", to="integrations.integrationapikey")),
                ("client", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="usage_records", to="integrations.integrationclient")),
            ],
            options={
                "ordering": ["-occurred_at", "-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="integrationusagerecord",
            index=models.Index(fields=["tool", "occurred_at"], name="integrations_tool_occ_idx"),
        ),
        migrations.AddIndex(
            model_name="integrationusagerecord",
            index=models.Index(fields=["client", "occurred_at"], name="integrations_client_occ_idx"),
        ),
        migrations.AddIndex(
            model_name="integrationusagerecord",
            index=models.Index(fields=["api_key", "occurred_at"], name="integrations_apikey_occ_idx"),
        ),
    ]
