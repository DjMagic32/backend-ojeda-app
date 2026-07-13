from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('store', '0024_inventario_pro_movimiento_stock'),
    ]

    operations = [
        migrations.CreateModel(
            name='ArticuloUsado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=120)),
                ('descripcion', models.TextField()),
                ('precio', models.DecimalField(decimal_places=2, max_digits=10)),
                ('moneda', models.CharField(choices=[('USD', 'USD'), ('VES', 'VES')], default='USD', max_length=3)),
                ('estado_articulo', models.CharField(choices=[('como_nuevo', 'Como nuevo'), ('buen_estado', 'Buen estado'), ('con_detalles', 'Con detalles')], max_length=15)),
                ('imagen', models.ImageField(blank=True, null=True, upload_to='articulos_usados/')),
                ('imagen_2', models.ImageField(blank=True, null=True, upload_to='articulos_usados/')),
                ('activo', models.BooleanField(default=True)),
                ('creado', models.DateTimeField(auto_now_add=True)),
                ('actualizado', models.DateTimeField(auto_now=True)),
                ('vendedor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='articulos_usados', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-creado'],
            },
        ),
    ]
