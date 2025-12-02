from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_officer_shareholder'),
    ]

    operations = [
        migrations.AlterField(
            model_name='company',
            name='vat_number',
            field=models.CharField(max_length=50, null=True, blank=True, verbose_name='Partita IVA'),
        ),
        migrations.AlterField(
            model_name='company',
            name='address',
            field=models.TextField(null=True, blank=True, verbose_name='Sede Legale'),
        ),
        migrations.AlterField(
            model_name='company',
            name='capital',
            field=models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, default=0, verbose_name='Capitale Sociale'),
        ),
    ]
