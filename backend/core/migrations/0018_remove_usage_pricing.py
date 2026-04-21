from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0017_delete_generateddocument"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="usagerecord",
            name="unit_price_eur",
        ),
        migrations.RemoveField(
            model_name="usagerecord",
            name="total_cost_eur",
        ),
        migrations.DeleteModel(
            name="UsageRate",
        ),
    ]
