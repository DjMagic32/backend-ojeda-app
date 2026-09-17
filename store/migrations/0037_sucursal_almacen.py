from django.db import migrations, models
import django.db.models.deletion


def crear_estructura_principal(apps, schema_editor):
    Negocio = apps.get_model('store', 'Negocio')
    Sucursal = apps.get_model('store', 'Sucursal')
    Almacen = apps.get_model('store', 'Almacen')

    for negocio in Negocio.objects.select_related('tienda').all().iterator():
        sucursal, _ = Sucursal.objects.get_or_create(
            negocio_id=negocio.pk,
            codigo='PRINCIPAL',
            defaults={
                'nombre': 'Principal',
                'direccion': negocio.tienda.direccion or '',
            },
        )
        Almacen.objects.get_or_create(
            sucursal_id=sucursal.pk,
            codigo='PRINCIPAL',
            defaults={'nombre': 'Almacén principal'},
        )


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0036_negocio_negociomiembro'),
    ]

    operations = [
        migrations.CreateModel(
            name='Sucursal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=120)),
                ('codigo', models.CharField(max_length=30)),
                ('direccion', models.TextField(blank=True, default='')),
                ('activo', models.BooleanField(default=True)),
                ('creado', models.DateTimeField(auto_now_add=True)),
                ('actualizado', models.DateTimeField(auto_now=True)),
                ('negocio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sucursales', to='store.negocio')),
            ],
            options={
                'ordering': ['nombre', 'id'],
            },
        ),
        migrations.CreateModel(
            name='Almacen',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=120)),
                ('codigo', models.CharField(max_length=30)),
                ('activo', models.BooleanField(default=True)),
                ('creado', models.DateTimeField(auto_now_add=True)),
                ('actualizado', models.DateTimeField(auto_now=True)),
                ('sucursal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='almacenes', to='store.sucursal')),
            ],
            options={
                'ordering': ['nombre', 'id'],
            },
        ),
        migrations.AddConstraint(
            model_name='sucursal',
            constraint=models.UniqueConstraint(fields=('negocio', 'codigo'), name='unique_codigo_sucursal_por_negocio'),
        ),
        migrations.AddConstraint(
            model_name='almacen',
            constraint=models.UniqueConstraint(fields=('sucursal', 'codigo'), name='unique_codigo_almacen_por_sucursal'),
        ),
        migrations.RunPython(crear_estructura_principal, migrations.RunPython.noop),
    ]
