from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('store', '0022_backfill_store_order_items'),
    ]

    operations = [
        migrations.AddField(
            model_name='tienda',
            name='verificada',
            field=models.BooleanField(default=False, help_text='Marcada manualmente por el administrador. Muestra el sello "Verificada" en la app.'),
        ),
        migrations.CreateModel(
            name='TarifaDelivery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tarifa_base', models.DecimalField(decimal_places=2, default=Decimal('1.00'), max_digits=10)),
                ('tarifa_por_km', models.DecimalField(decimal_places=2, default=Decimal('0.50'), max_digits=10)),
                ('costo_minimo', models.DecimalField(decimal_places=2, default=Decimal('1.00'), max_digits=10)),
                ('activa', models.BooleanField(default=True)),
                ('actualizado', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Tarifa de delivery',
                'verbose_name_plural': 'Tarifas de delivery',
                'ordering': ['-actualizado'],
            },
        ),
        migrations.CreateModel(
            name='Reporte',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('motivo', models.CharField(choices=[('producto_enganoso', 'Producto o servicio engañoso'), ('estafa', 'Posible estafa o fraude'), ('contenido_inapropiado', 'Contenido inapropiado'), ('spam', 'Spam o publicaciones repetidas'), ('otro', 'Otro')], max_length=30)),
                ('descripcion', models.TextField(blank=True)),
                ('estado', models.CharField(choices=[('pendiente', 'Pendiente'), ('revisado', 'Revisado')], default='pendiente', max_length=15)),
                ('creado', models.DateTimeField(auto_now_add=True)),
                ('producto', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='reportes', to='store.productotienda')),
                ('reportante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reportes', to=settings.AUTH_USER_MODEL)),
                ('tienda', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='reportes', to='store.tienda')),
            ],
            options={
                'ordering': ['-creado'],
            },
        ),
    ]
