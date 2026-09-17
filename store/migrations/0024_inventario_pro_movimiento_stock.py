import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0023_tienda_verificada_tarifadelivery_reporte'),
    ]

    operations = [
        migrations.AddField(
            model_name='productotienda',
            name='costo_unitario',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Costo de adquisición, para cálculo de margen (visible solo para la tienda).', max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='productotienda',
            name='codigo_barras',
            field=models.CharField(blank=True, db_index=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name='storeorder',
            name='canal',
            field=models.CharField(choices=[('online', 'En línea'), ('presencial', 'Presencial')], default='online', max_length=15),
        ),
        migrations.CreateModel(
            name='MovimientoStock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('entrada', 'Entrada'), ('venta', 'Venta'), ('ajuste', 'Ajuste')], max_length=10)),
                ('cantidad', models.IntegerField(help_text='Delta con signo: las ventas son negativas.')),
                ('stock_resultante', models.PositiveIntegerField(blank=True, null=True)),
                ('origen', models.CharField(choices=[('venta_presencial', 'Venta presencial'), ('orden_online', 'Orden en línea'), ('ajuste_manual', 'Ajuste manual'), ('creacion', 'Creación de producto')], max_length=20)),
                ('creado', models.DateTimeField(auto_now_add=True)),
                ('order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='movimientos_stock', to='store.storeorder')),
                ('producto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='movimientos_stock', to='store.productotienda')),
            ],
            options={
                'ordering': ['-creado'],
            },
        ),
        migrations.AddIndex(
            model_name='movimientostock',
            index=models.Index(fields=['producto', '-creado'], name='store_movim_product_idx'),
        ),
        migrations.AddConstraint(
            model_name='productotienda',
            constraint=models.UniqueConstraint(condition=models.Q(('codigo_barras__isnull', False)), fields=('tienda', 'codigo_barras'), name='unique_codigo_barras_por_tienda'),
        ),
    ]
