from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0024_savednewsletter_metadata"),
    ]

    operations = [
        migrations.AlterField(
            model_name="usagerecord",
            name="tool",
            field=models.CharField(
                choices=[
                    ("RICERCA_DOCUMENTALE", "Ricerca documentale"),
                    ("DRAFT_DOCUMENT", "Draft document"),
                    ("CHECK_COMPLIANCE", "Check compliance"),
                    ("CHAT_ASSISTANT", "Chat assistant"),
                    ("NEWSLETTER_PILL", "Newsletter & PILL"),
                    ("SEGRETERIA_SOCIETARIA", "Segreteria societaria"),
                ],
                max_length=64,
            ),
        ),
    ]
