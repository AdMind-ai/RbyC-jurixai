from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("integrations", "0008_rename_integration_client__ca25f1_idx_integration_client__3144c7_idx_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="documentindex",
            name="approval_date",
        ),
    ]
