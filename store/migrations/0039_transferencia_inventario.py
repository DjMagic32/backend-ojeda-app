from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0038_inventario_almacen'),
    ]

    operations = [
        migrations.CreateModel(
            name='TransferenciaInventario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad', models.PositiveIntegerField()),
                ('notas', models.TextField(blank=True, default='')),
                ('creado', models.DateTimeField(auto_now_add=True)),
                ('almacen_destino', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='transferencias_entrada', to='store.almacen')),
                ('almacen_origen', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='transferencias_salida', to='store.almacen')),
                ('creado_por', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='transferencias_inventario_creadas', to='store.usuario')),
                ('producto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transferencias_inventario', to='store.productotienda')),
            ],
            options={
                'ordering': ['-creado', '-id'],
            },
        ),
        migrations.AddField(
            model_name='movimientostock',
            name='transferencia',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='movimientos_stock', to='store.transferenciainventario'),
        ),
        migrations.AlterField(
            model_name='movimientostock',
            name='tipo',
            field=models.CharField(choices=[('entrada', 'Entrada'), ('venta', 'Venta'), ('ajuste', 'Ajuste'), ('transferencia', 'Transferencia')], max_length=15),
        ),
        migrations.AddIndex(
            model_name='transferenciainventario',
            index=models.Index(fields=['producto', '-creado'], name='store_transfer_product_idx'),
        ),
        migrations.AddIndex(
            model_name='transferenciainventario',
            index=models.Index(fields=['almacen_origen', '-creado'], name='store_transfer_origin_idx'),
        ),
        migrations.AddIndex(
            model_name='transferenciainventario',
            index=models.Index(fields=['almacen_destino', '-creado'], name='store_transfer_dest_idx'),
        ),
    ]
