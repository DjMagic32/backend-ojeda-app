from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('store', '0043_cuentas_por_pagar')]

    operations = [
        migrations.CreateModel(
            name='Gasto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tienda_id', models.PositiveBigIntegerField()),
                ('sucursal_id', models.PositiveBigIntegerField(blank=True, null=True)),
                ('tipo', models.CharField(choices=[('fijo', 'Fijo'), ('variable', 'Variable')], max_length=10)),
                ('categoria', models.CharField(max_length=100)),
                ('descripcion', models.TextField(blank=True, default='')),
                ('monto', models.DecimalField(decimal_places=2, max_digits=14)),
                ('moneda', models.CharField(choices=[('USD', 'Dólares (USD)'), ('VES', 'Bolívares (VES)')], default='USD', max_length=3)),
                ('tasa_aplicada', models.DecimalField(blank=True, decimal_places=4, help_text='Tasa USD→VES vigente al registrar el gasto (snapshot).', max_digits=12, null=True)),
                ('anulado', models.BooleanField(default=False)),
                ('notas', models.TextField(blank=True, default='')),
                ('registrado_por', models.PositiveBigIntegerField()),
                ('creado', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-creado'],
                'indexes': [
                    models.Index(fields=('tienda_id', '-creado'), name='store_gasto_tienda_idx'),
                    models.Index(fields=('tienda_id', 'sucursal_id', '-creado'), name='store_gasto_sucursal_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='OperacionGasto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tienda_id', models.PositiveBigIntegerField()),
                ('clave', models.UUIDField()),
                ('huella', models.CharField(blank=True, default='', max_length=64)),
                ('respuesta', models.JSONField(blank=True, null=True)),
                ('cancelada', models.BooleanField(default=False)),
                ('creado', models.DateTimeField(auto_now_add=True)),
            ],
            options={'constraints': [models.UniqueConstraint(fields=('tienda_id', 'clave'), name='unique_operacion_gasto_tienda')]},
        ),
    ]
