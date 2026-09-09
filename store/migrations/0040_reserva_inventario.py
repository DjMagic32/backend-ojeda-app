from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0039_transferencia_inventario'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReservaInventario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad', models.PositiveIntegerField()),
                ('expira_en', models.DateTimeField()),
                ('estado', models.CharField(choices=[('activa', 'Activa'), ('consumida', 'Consumida'), ('liberada', 'Liberada'), ('expirada', 'Expirada')], default='activa', max_length=12)),
                ('creado', models.DateTimeField(auto_now_add=True)),
                ('actualizado', models.DateTimeField(auto_now=True)),
                ('almacen', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reservas_inventario', to='store.almacen')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reservas', to='store.storeorder')),
                ('producto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reservas_inventario', to='store.productotienda')),
            ],
        ),
        migrations.AddIndex(
            model_name='reservainventario',
            index=models.Index(fields=['producto', 'estado'], name='store_reserva_product_state_idx'),
        ),
        migrations.AddIndex(
            model_name='reservainventario',
            index=models.Index(fields=['order', 'estado'], name='store_reserva_order_state_idx'),
        ),
    ]
