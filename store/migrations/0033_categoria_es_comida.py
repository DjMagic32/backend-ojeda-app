from django.db import migrations, models


def marcar_categorias_de_comida(apps, schema_editor):
    Categoria = apps.get_model('store', 'Categoria')
    nombres_comida = {
        'comida',
        'alimento',
        'alimentos',
        'alimentacion',
        'restaurante',
        'restaurantes',
    }
    for categoria in Categoria.objects.all():
        nombre = (categoria.nombre or '').strip().casefold()
        if nombre in nombres_comida:
            categoria.es_comida = True
            categoria.save(update_fields=['es_comida'])


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0032_tienda_reputacion'),
    ]

    operations = [
        migrations.AddField(
            model_name='categoria',
            name='es_comida',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text='Indica si la categoría se muestra en la sección Comidas.',
            ),
        ),
        migrations.RunPython(
            marcar_categorias_de_comida,
            migrations.RunPython.noop,
        ),
    ]
