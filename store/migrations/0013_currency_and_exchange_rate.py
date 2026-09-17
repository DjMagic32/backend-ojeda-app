from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0012_chat_pushtoken'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='productotienda',
            name='moneda',
            field=models.CharField(
                choices=[('USD', 'Dólares (USD)'), ('VES', 'Bolívares (VES)')],
                default='USD',
                max_length=3,
            ),
        ),
        migrations.AddField(
            model_name='storeorder',
            name='moneda',
            field=models.CharField(
                choices=[('USD', 'Dólares (USD)'), ('VES', 'Bolívares (VES)')],
                default='USD',
                max_length=3,
            ),
        ),
        migrations.AddField(
            model_name='storeorder',
            name='tasa_aplicada',
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text='Tasa USD→VES vigente al crear la orden (snapshot).',
                max_digits=12,
                null=True,
            ),
        ),
        migrations.CreateModel(
            name='TasaCambio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valor_bs', models.DecimalField(
                    decimal_places=4,
                    help_text='Cuántos bolívares equivalen a 1 USD.',
                    max_digits=12,
                )),
                ('fuente', models.CharField(
                    choices=[('BCV', 'BCV'), ('PARALELO', 'Paralelo'), ('MANUAL', 'Manual')],
                    default='BCV',
                    max_length=15,
                )),
                ('creado', models.DateTimeField(auto_now_add=True)),
                ('registrado_por', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=models.deletion.SET_NULL,
                    related_name='tasas_registradas',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-creado'],
                'indexes': [models.Index(fields=['-creado'], name='store_tasac_creado_idx')],
            },
        ),
    ]
