from datetime import datetime
import re

from django.db import migrations, models


def infer_document_date(object_key: str):
    value = object_key or ""
    date_patterns = (
        (lambda groups: f"{groups[0]}{groups[1]}{groups[2]}", "%d%m%Y", r"(?<!\d)(\d{2})(\d{2})(20\d{2})(?!\d)"),
        (lambda groups: f"{groups[0]}-{groups[1]}-{groups[2]}", "%d-%m-%Y", r"(?<!\d)(\d{2})[-_./](\d{2})[-_./](20\d{2})(?!\d)"),
        (lambda groups: f"{groups[0]}{groups[1]}{groups[2]}", "%Y%m%d", r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)"),
    )

    for builder, date_format, pattern in date_patterns:
        match = re.search(pattern, value, flags=re.IGNORECASE)
        if not match:
            continue
        try:
            return datetime.strptime(builder(match.groups()), date_format).date()
        except ValueError:
            continue

    return None


def backfill_semantic_dates(apps, schema_editor):
    DocumentIndex = apps.get_model("integrations", "DocumentIndex")

    for document in DocumentIndex.objects.all().only(
        "id",
        "object_key",
        "last_modified",
        "s3_last_modified",
        "document_date",
    ):
        update_fields = []

        if document.s3_last_modified is None and document.last_modified is not None:
            document.s3_last_modified = document.last_modified
            update_fields.append("s3_last_modified")

        if document.document_date is None:
            inferred_date = infer_document_date(document.object_key)
            if inferred_date is not None:
                document.document_date = inferred_date
                update_fields.append("document_date")

        if update_fields:
            document.save(update_fields=update_fields)


class Migration(migrations.Migration):

    dependencies = [
        ("integrations", "0005_documentindex_topic_tags"),
    ]

    operations = [
        migrations.AddField(
            model_name="documentindex",
            name="document_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="documentindex",
            name="s3_last_modified",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="documentindex",
            index=models.Index(
                fields=["client", "active", "document_date"],
                name="integratio_client__semdate_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="documentindex",
            index=models.Index(
                fields=["client", "active", "s3_last_modified"],
                name="integratio_client__s3lmod_idx",
            ),
        ),
        migrations.RunPython(backfill_semantic_dates, migrations.RunPython.noop),
    ]
