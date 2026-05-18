from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("integrations", "0009_remove_documentindex_approval_date"),
    ]

    operations = [
        migrations.AddField(
            model_name="documentindex",
            name="search_text",
            field=models.TextField(blank=True),
        ),
    ]
