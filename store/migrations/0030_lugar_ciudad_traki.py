from django.db import migrations


def crear_ciudad_traki(apps, schema_editor):
    Lugar = apps.get_model('store', 'Lugar')
    Lugar.objects.update_or_create(
        nombre='Ciudad Traki',
        defaults={
            'alias': 'Centro Traki, Traki Ciudad Ojeda, Traki Las Morochas',
            'categoria': 'centro_comercial',
            'direccion': (
                'Av. Intercomunal entre calles Amparo y Padre Olivares, '
                'Las Morochas II, Ciudad Ojeda'
            ),
            'lat': 10.198563,
            'lng': -71.325563,
            'activo': True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ('store', '0029_lugar_catalogo_local'),
    ]

    operations = [
        migrations.RunPython(crear_ciudad_traki, migrations.RunPython.noop),
    ]
