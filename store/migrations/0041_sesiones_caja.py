from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('store', '0040_operacion_venta_presencial')]

    operations = [
        migrations.CreateModel(
            name='SesionCaja',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tienda_id', models.PositiveBigIntegerField()),
                ('almacen_id', models.PositiveBigIntegerField()),
                ('almacen_nombre', models.CharField(max_length=120)),
                ('sucursal_nombre', models.CharField(max_length=120)),
                ('abierta', models.BooleanField(default=True)),
                ('fondo_usd', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('fondo_ves', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('contado_usd', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('contado_ves', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('esperado_usd', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('esperado_ves', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('abierto_por', models.PositiveBigIntegerField()),
                ('cerrado_por', models.PositiveBigIntegerField(blank=True, null=True)),
                ('notas_cierre', models.TextField(blank=True, default='')),
                ('abierto', models.DateTimeField(auto_now_add=True)),
                ('cerrado', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'ordering': ['-id'],
                'constraints': [models.UniqueConstraint(fields=('tienda_id', 'almacen_id'), condition=models.Q(abierta=True), name='unique_caja_abierta_almacen')],
                'indexes': [models.Index(fields=['tienda_id', '-id'], name='store_caja_tienda_idx')],
            },
        ),
        migrations.CreateModel(
            name='MovimientoCaja',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('venta', 'Venta'), ('entrada', 'Entrada'), ('retiro', 'Retiro')], max_length=10)),
                ('moneda', models.CharField(choices=[('USD', 'Dólares (USD)'), ('VES', 'Bolívares (VES)')], max_length=3)),
                ('monto', models.DecimalField(decimal_places=2, max_digits=20)),
                ('medio_pago', models.CharField(choices=[('efectivo', 'Efectivo'), ('pago_movil', 'Pago móvil'), ('zelle', 'Zelle'), ('tarjeta', 'Tarjeta'), ('transferencia', 'Transferencia')], default='efectivo', max_length=20)),
                ('motivo', models.TextField(blank=True, default='')),
                ('usuario_id', models.PositiveBigIntegerField()),
                ('order_id', models.PositiveBigIntegerField(blank=True, null=True, unique=True)),
                ('creado', models.DateTimeField(auto_now_add=True)),
                ('sesion', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='movimientos', to='store.sesioncaja')),
            ],
            options={'ordering': ['-id']},
        ),
        migrations.CreateModel(
            name='OperacionCaja',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tienda_id', models.PositiveBigIntegerField()),
                ('clave', models.UUIDField()),
                ('huella', models.CharField(blank=True, default='', max_length=64)),
                ('respuesta', models.JSONField(blank=True, null=True)),
                ('cancelada', models.BooleanField(default=False)),
                ('creado', models.DateTimeField(auto_now_add=True)),
            ],
            options={'constraints': [models.UniqueConstraint(fields=('tienda_id', 'clave'), name='unique_operacion_caja_tienda')]},
        ),
    ]
