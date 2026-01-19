from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0009_categoria_thumbnail'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notificacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=255)),
                ('mensaje', models.TextField(blank=True)),
                ('tipo', models.CharField(choices=[('favorite', 'Favorito'), ('order', 'Orden'), ('service', 'Servicio'), ('general', 'General')], default='general', max_length=20)),
                ('leido', models.BooleanField(default=False)),
                ('creado', models.DateTimeField(auto_now_add=True)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notificaciones', to='store.usuario')),
            ],
            options={
                'ordering': ['-creado'],
            },
        ),
    ]
