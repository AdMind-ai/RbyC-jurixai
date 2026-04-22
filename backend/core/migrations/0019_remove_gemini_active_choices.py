# Generated manually to remove Gemini from active chat and usage choices.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0018_remove_usage_pricing"),
    ]

    operations = [
        migrations.AlterField(
            model_name="storedchatsession",
            name="provider",
            field=models.CharField(
                choices=[
                    ("gpt", "GPT / OpenAI"),
                    ("perplexity", "Perplexity"),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="usagerecord",
            name="sub_tool",
            field=models.CharField(
                blank=True,
                choices=[
                    ("GPT-5.2", "GPT-5.2"),
                    ("PERPLEXITY", "Perplexity"),
                    ("DOCUMENTI_AI", "Documenti AI"),
                    ("ASSISTENTE_LEGALE", "Assistente legale"),
                ],
                max_length=64,
                null=True,
            ),
        ),
    ]
