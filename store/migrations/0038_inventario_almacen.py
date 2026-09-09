from django.db import migrations, models
import django.db.models.deletion


def migrar_stock_al_almacen_principal(apps, schema_editor):
    ProductoTienda = apps.get_model('store', 'ProductoTienda')
    Almacen = apps.get_model('store', 'Almacen')
    InventarioAlmacen = apps.get_model('store', 'InventarioAlmacen')

    for producto in ProductoTienda.objects.filter(stock__isnull=False).iterator():
        almacen = (
            Almacen.objects.filter(
                sucursal__negocio__tienda_id=producto.tienda_id,
                sucursal__activo=True,
                activo=True,
                codigo='PRINCIPAL',
            )
            .order_by('id')
            .first()
        )
        if almacen is not None:
            InventarioAlmacen.objects.get_or_create(
                producto_id=producto.pk,
                almacen_id=almacen.pk,
                defaults={'cantidad': producto.stock},
            )


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0037_sucursal_almacen'),
    ]

    operations = [
        migrations.CreateModel(
            name='InventarioAlmacen',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad', models.PositiveIntegerField(default=0)),
                ('actualizado', models.DateTimeField(auto_now=True)),
                ('almacen', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='existencias', to='store.almacen')),
                ('producto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='existencias_almacen', to='store.productotienda')),
            ],
        ),
        migrations.AddField(
            model_name='movimientostock',
            name='almacen',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='movimientos_stock', to='store.almacen'),
        ),
        migrations.AddField(
            model_name='movimientostock',
            name='stock_almacen_resultante',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name='inventarioalmacen',
            constraint=models.UniqueConstraint(fields=('almacen', 'producto'), name='unique_existencia_producto_almacen'),
        ),
        migrations.AddIndex(
            model_name='inventarioalmacen',
            index=models.Index(fields=['producto', 'almacen'], name='store_inv_product_wh_idx'),
        ),
        migrations.AddIndex(
            model_name='inventarioalmacen',
            index=models.Index(fields=['almacen', 'producto'], name='store_inv_wh_product_idx'),
        ),
        migrations.RunPython(migrar_stock_al_almacen_principal, migrations.RunPython.noop),
    ]
