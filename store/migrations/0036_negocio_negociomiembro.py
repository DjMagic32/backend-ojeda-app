from django.db import migrations, models
import django.db.models.deletion


def crear_negocios_existentes(apps, schema_editor):
    Tienda = apps.get_model('store', 'Tienda')
    Negocio = apps.get_model('store', 'Negocio')
    NegocioMiembro = apps.get_model('store', 'NegocioMiembro')

    for tienda in Tienda.objects.all().iterator():
        negocio, _ = Negocio.objects.get_or_create(
            tienda_id=tienda.pk,
            defaults={'nombre_legal': tienda.nombre},
        )
        NegocioMiembro.objects.get_or_create(
            negocio_id=negocio.pk,
            usuario_id=tienda.usuario_id,
            defaults={'rol': 'owner'},
        )


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0035_seed_catalog_categories'),
    ]

    operations = [
        migrations.CreateModel(
            name='Negocio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre_legal', models.CharField(blank=True, default='', max_length=200)),
                ('activo', models.BooleanField(default=True)),
                ('creado', models.DateTimeField(auto_now_add=True)),
                ('actualizado', models.DateTimeField(auto_now=True)),
                ('tienda', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='negocio', to='store.tienda')),
            ],
        ),
        migrations.CreateModel(
            name='NegocioMiembro',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rol', models.CharField(choices=[('owner', 'Propietario'), ('admin', 'Administrador')], default='admin', max_length=20)),
                ('activo', models.BooleanField(default=True)),
                ('creado', models.DateTimeField(auto_now_add=True)),
                ('actualizado', models.DateTimeField(auto_now=True)),
                ('negocio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='miembros', to='store.negocio')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='membresias_negocio', to='store.usuario')),
            ],
        ),
        migrations.AddConstraint(
            model_name='negociomiembro',
            constraint=models.UniqueConstraint(fields=('negocio', 'usuario'), name='unique_miembro_por_negocio'),
        ),
        migrations.AddIndex(
            model_name='negociomiembro',
            index=models.Index(fields=['usuario', 'activo'], name='store_member_user_active_idx'),
        ),
        migrations.RunPython(crear_negocios_existentes, migrations.RunPython.noop),
    ]
