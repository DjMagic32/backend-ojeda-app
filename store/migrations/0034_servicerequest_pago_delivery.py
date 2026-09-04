from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0033_categoria_es_comida'),
    ]

    operations = [
        migrations.AddField(
            model_name='servicerequest',
            name='pago_delivery',
            field=models.CharField(
                choices=[
                    ('destination', 'Pago en destino'),
                    ('store', 'Lo paga la tienda'),
                ],
                default='destination',
                help_text='Define quién asume el costo del delivery.',
                max_length=20,
            ),
        ),
    ]
