from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('store', '0039_transferencia_inventario')]

    operations = [
        migrations.CreateModel(
            name='OperacionVentaPresencial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tienda_id', models.PositiveBigIntegerField()),
                ('clave', models.UUIDField()),
                ('huella', models.CharField(blank=True, default='', max_length=64)),
                ('respuesta', models.JSONField(blank=True, null=True)),
                ('cancelada', models.BooleanField(default=False)),
                ('creado', models.DateTimeField(auto_now_add=True)),
            ],
            options={'constraints': [models.UniqueConstraint(
                fields=('tienda_id', 'clave'), name='unique_operacion_venta_tienda',
            )]},
        ),
    ]
