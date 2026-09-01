from django.db import migrations, models
import django.db.models.deletion


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
    ]
