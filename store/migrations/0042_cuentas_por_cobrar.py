from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('store', '0041_sesiones_caja')]

    operations = [
        migrations.CreateModel(
            name='CuentaPorCobrar',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tienda_id', models.PositiveBigIntegerField()),
                ('cliente_nombre', models.CharField(max_length=200)),
                ('cliente_telefono', models.CharField(blank=True, default='', max_length=20)),
                ('order_id', models.PositiveBigIntegerField(blank=True, null=True)),
                ('monto_usd', models.DecimalField(decimal_places=2, max_digits=14)),
                ('saldo_usd', models.DecimalField(decimal_places=2, max_digits=14)),
                ('tasa_emision', models.DecimalField(decimal_places=4, max_digits=12)),
                ('estado', models.CharField(choices=[('pendiente', 'Pendiente'), ('parcial', 'Abonada parcialmente'), ('pagada', 'Pagada'), ('anulada', 'Anulada')], default='pendiente', max_length=15)),
                ('vencimiento', models.DateField(blank=True, null=True)),
                ('notas', models.TextField(blank=True, default='')),
                ('creado_por', models.PositiveBigIntegerField()),
                ('creado', models.DateTimeField(auto_now_add=True)),
                ('actualizado', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-creado'],
                'indexes': [
                    models.Index(fields=('tienda_id', 'estado'), name='store_cxc_tienda_estado_idx'),
                    models.Index(fields=('tienda_id', 'vencimiento'), name='store_cxc_tienda_venc_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='AbonoCuentaPorCobrar',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('monto_usd', models.DecimalField(decimal_places=2, max_digits=14)),
                ('tasa_liquidacion', models.DecimalField(decimal_places=4, max_digits=12)),
                ('monto_ves_equivalente', models.DecimalField(decimal_places=2, max_digits=16)),
                ('diferencial_cambiario_ves', models.DecimalField(decimal_places=2, max_digits=16)),
                ('medio_pago', models.CharField(choices=[('efectivo', 'Efectivo'), ('pago_movil', 'Pago móvil'), ('zelle', 'Zelle'), ('tarjeta', 'Tarjeta'), ('transferencia', 'Transferencia')], default='efectivo', max_length=20)),
                ('registrado_por', models.PositiveBigIntegerField()),
                ('creado', models.DateTimeField(auto_now_add=True)),
                ('cuenta', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='abonos', to='store.cuentaporcobrar')),
            ],
            options={'ordering': ['-creado']},
        ),
        migrations.CreateModel(
            name='OperacionCuentaPorCobrar',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tienda_id', models.PositiveBigIntegerField()),
                ('clave', models.UUIDField()),
                ('huella', models.CharField(blank=True, default='', max_length=64)),
                ('respuesta', models.JSONField(blank=True, null=True)),
                ('cancelada', models.BooleanField(default=False)),
                ('creado', models.DateTimeField(auto_now_add=True)),
            ],
            options={'constraints': [models.UniqueConstraint(fields=('tienda_id', 'clave'), name='unique_operacion_cxc_tienda')]},
        ),
    ]
