from django.db import migrations, models
import django.db.models.deletion


def poblar_destinos_recientes(apps, schema_editor):
    DestinoReciente = apps.get_model('store', 'DestinoReciente')
    ServiceRequest = apps.get_model('store', 'ServiceRequest')

    usados_por_usuario = {}
    cantidad_por_usuario = {}
    servicios = ServiceRequest.objects.filter(
        estado='completed',
        dropoff_lat__isnull=False,
        dropoff_lng__isnull=False,
    ).order_by('cliente_id', '-completado_en', '-id')

    for servicio in servicios:
        usuario_id = servicio.cliente_id
        if cantidad_por_usuario.get(usuario_id, 0) >= 3:
            continue

        coordenadas = (
            usuario_id,
            str(servicio.dropoff_lat),
            str(servicio.dropoff_lng),
        )
        usados = usados_por_usuario.setdefault(usuario_id, set())
        if coordenadas in usados:
            continue

        direccion = (servicio.dropoff_direccion or '').strip()[:255]
        nombre = (direccion.split(',', 1)[0].strip() or 'Destino en el mapa')[:160]
        reciente = DestinoReciente.objects.create(
            usuario_id=usuario_id,
            nombre=nombre,
            direccion=direccion,
            lat=servicio.dropoff_lat,
            lng=servicio.dropoff_lng,
            veces_usado=1,
        )
        fecha = servicio.completado_en or servicio.actualizado
        if fecha:
            DestinoReciente.objects.filter(pk=reciente.pk).update(ultima_vez=fecha)

        usados.add(coordenadas)
        cantidad_por_usuario[usuario_id] = cantidad_por_usuario.get(usuario_id, 0) + 1


class Migration(migrations.Migration):
    dependencies = [
        ('store', '0030_lugar_ciudad_traki'),
    ]

    operations = [
        migrations.CreateModel(
            name='DestinoReciente',
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
                ('nombre', models.CharField(max_length=160)),
                ('direccion', models.CharField(blank=True, default='', max_length=255)),
                ('lat', models.DecimalField(decimal_places=6, max_digits=9)),
                ('lng', models.DecimalField(decimal_places=6, max_digits=9)),
                ('veces_usado', models.PositiveIntegerField(default=1)),
                ('ultima_vez', models.DateTimeField(auto_now=True)),
                ('creado', models.DateTimeField(auto_now_add=True)),
                (
                    'usuario',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='destinos_recientes',
                        to='store.usuario',
                    ),
                ),
            ],
            options={
                'ordering': ['-ultima_vez', '-id'],
                'indexes': [
                    models.Index(
                        fields=['usuario', '-ultima_vez'],
                        name='store_destino_reciente_user_idx',
                    ),
                ],
                'constraints': [
                    models.UniqueConstraint(
                        fields=('usuario', 'lat', 'lng'),
                        name='unique_recent_destination_coordinates',
                    ),
                ],
            },
        ),
        migrations.RunPython(poblar_destinos_recientes, migrations.RunPython.noop),
    ]
