import re
import unicodedata
from datetime import datetime

from django.db import migrations, models


def infer_approval_date(text_preview: str):
    preview = (text_preview or "").strip()
    if not preview:
        return None

    normalized = unicodedata.normalize("NFKD", preview)
    normalized = "".join(
        char for char in normalized if not unicodedata.combining(char)
    ).lower()
    normalized = " ".join(normalized.split())

    month_map = {
        "gennaio": 1,
        "febbraio": 2,
        "marzo": 3,
        "aprile": 4,
        "maggio": 5,
        "giugno": 6,
        "luglio": 7,
        "agosto": 8,
        "settembre": 9,
        "ottobre": 10,
        "novembre": 11,
        "dicembre": 12,
    }

    textual_patterns = (
        r"(?:approvat\w*|approvazione|deliberat\w*|delibera\w*)[^.\n]{0,80}?\b(\d{1,2})\s+"
        r"(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)"
        r"\s+(20\d{2})\b",
    )
    for pattern in textual_patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if not match:
            continue
        day = int(match.group(1))
        month = month_map.get(match.group(2).lower())
        year = int(match.group(3))
        if not month:
            continue
        try:
            return datetime(year, month, day).date()
        except ValueError:
            continue

    numeric_patterns = (
        r"(?:approvat\w*|approvazione|deliberat\w*|delibera\w*)[^.\n]{0,80}?\b(\d{2})[\/._-](\d{2})[\/._-](20\d{2})\b",
    )
    for pattern in numeric_patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if not match:
            continue
        try:
            return datetime(
                int(match.group(3)),
                int(match.group(2)),
                int(match.group(1)),
            ).date()
        except ValueError:
            continue

    return None


def backfill_approval_date(apps, schema_editor):
    DocumentIndex = apps.get_model("integrations", "DocumentIndex")

    for document in DocumentIndex.objects.all().only(
        "id",
        "text_preview",
        "approval_date",
    ):
        if document.approval_date is not None:
            continue
        inferred_date = infer_approval_date(document.text_preview)
        if inferred_date is None:
            continue
        document.approval_date = inferred_date
        document.save(update_fields=["approval_date"])


class Migration(migrations.Migration):

    dependencies = [
        ("integrations", "0006_documentindex_semantic_dates"),
    ]

    operations = [
        migrations.AddField(
            model_name="documentindex",
            name="approval_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="documentindex",
            index=models.Index(
                fields=["client", "active", "approval_date"],
                name="integratio_client__appdate_idx",
            ),
        ),
        migrations.RunPython(backfill_approval_date, migrations.RunPython.noop),
    ]
