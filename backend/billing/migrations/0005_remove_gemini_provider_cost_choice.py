# Generated manually to remove Gemini from provider billing costs.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0004_providerusagecost"),
    ]

    operations = [
        migrations.AlterField(
            model_name="providermonthlycost",
            name="provider",
            field=models.CharField(
                choices=[
                    ("openai", "OpenAI"),
                    ("perplexity", "Perplexity"),
                ],
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="providerusagecost",
            name="provider",
            field=models.CharField(
                choices=[
                    ("openai", "OpenAI"),
                    ("perplexity", "Perplexity"),
                ],
                max_length=32,
            ),
        ),
    ]
