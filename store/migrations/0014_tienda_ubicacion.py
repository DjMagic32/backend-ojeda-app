from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0013_currency_and_exchange_rate'),
    ]

    operations = [
        migrations.AddField(
            model_name='tienda',
            name='ubicacion_lat',
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                max_digits=9,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='tienda',
            name='ubicacion_lng',
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                max_digits=9,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='tienda',
            name='ubicacion_actualizada',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
