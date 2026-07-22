from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0023_saved_newsletter_notification"),
    ]

    operations = [
        migrations.AddField(
            model_name="savednewsletter",
            name="metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
