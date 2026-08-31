from django.db import migrations, models


def crear_lugares_iniciales(apps, schema_editor):
    Lugar = apps.get_model('store', 'Lugar')
    Lugar.objects.update_or_create(
        nombre='Hospital Dr. Pedro García Clara',
        defaults={
            'alias': (
                'Hospital Pedro Garcia Clara, Hospital Pedro García Clara, '
                'Hospital de Ciudad Ojeda'
            ),
            'categoria': 'hospital',
            'direccion': 'Av. 34 frente al Barrio Obrero, Ciudad Ojeda',
            'lat': 10.20898,
            'lng': -71.31029,
            'activo': True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ('store', '0028_servicerequestcandidate'),
    ]

    operations = [
        migrations.CreateModel(
            name='Lugar',
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
                (
                    'alias',
                    models.TextField(
                        blank=True,
                        default='',
                        help_text='Nombres alternativos separados por coma para mejorar la búsqueda.',
                    ),
                ),
                (
                    'categoria',
                    models.CharField(
                        choices=[
                            ('hospital', 'Hospital'),
                            ('clinica', 'Clínica'),
                            ('centro_comercial', 'Centro comercial'),
                            ('mercado', 'Mercado'),
                            ('local', 'Local'),
                            ('otro', 'Otro'),
                        ],
                        default='otro',
                        max_length=30,
                    ),
                ),
                ('direccion', models.CharField(blank=True, default='', max_length=255)),
                ('lat', models.DecimalField(decimal_places=6, max_digits=9)),
                ('lng', models.DecimalField(decimal_places=6, max_digits=9)),
                ('activo', models.BooleanField(default=True)),
                ('creado', models.DateTimeField(auto_now_add=True)),
                ('actualizado', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['nombre'],
                'indexes': [
                    models.Index(
                        fields=['activo', 'categoria'],
                        name='store_lugar_activo_cat_idx',
                    ),
                ],
            },
        ),
        migrations.RunPython(crear_lugares_iniciales, migrations.RunPython.noop),
    ]
