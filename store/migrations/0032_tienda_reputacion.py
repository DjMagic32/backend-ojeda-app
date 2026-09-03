from django.db import migrations, models
import django.db.models.deletion


def crear_historial_nombres(apps, schema_editor):
    Tienda = apps.get_model('store', 'Tienda')
    TiendaNombreHistorial = apps.get_model('store', 'TiendaNombreHistorial')
    TiendaNombreHistorial.objects.bulk_create(
        [
            TiendaNombreHistorial(tienda_id=tienda.id, nombre=tienda.nombre)
            for tienda in Tienda.objects.only('id', 'nombre').iterator()
        ]
    )


class Migration(migrations.Migration):
    dependencies = [
        ('store', '0031_message_adjuntos'),
    ]

    operations = [
        migrations.CreateModel(
            name='TiendaNombreHistorial',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('nombre', models.CharField(max_length=200)),
                ('creado', models.DateTimeField(auto_now_add=True)),
                (
                    'tienda',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='historial_nombres',
                        to='store.tienda',
                    ),
                ),
            ],
            options={
                'ordering': ['-creado'],
                'indexes': [
                    models.Index(
                        fields=['tienda', '-creado'],
                        name='store_tienda_nombre_hist_idx',
                    ),
                ],
            },
        ),
        migrations.AddField(
            model_name='storeorderreview',
            name='etiquetas',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RunPython(crear_historial_nombres, migrations.RunPython.noop),
    ]
