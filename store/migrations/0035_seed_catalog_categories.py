from django.db import migrations


PRODUCT_CATEGORIES = (
    ('Comida', 'Alimentos, bebidas y productos preparados.', True),
    ('Tecnología', 'Dispositivos, accesorios y soluciones tecnológicas.', False),
    ('Hogar', 'Artículos, decoración y servicios para el hogar.', False),
    ('Moda', 'Ropa, calzado y accesorios.', False),
    ('Belleza', 'Cuidado personal, cosmética y bienestar.', False),
    ('Salud', 'Productos relacionados con salud y cuidado.', False),
    ('Deportes', 'Artículos y equipamiento deportivo.', False),
    ('Educación', 'Materiales, libros y recursos educativos.', False),
    ('Vehículos', 'Vehículos, repuestos y accesorios.', False),
    ('Mascotas', 'Alimentos, accesorios y cuidado de mascotas.', False),
    ('Oficina', 'Papelería, mobiliario y artículos de oficina.', False),
    ('Otros', 'Productos que no pertenecen a otra categoría.', False),
)

SERVICE_CATEGORIES = (
    ('Servicios profesionales', 'Asesorías, consultorías y servicios especializados.'),
    ('Reparaciones y mantenimiento', 'Reparación, instalación y mantenimiento.'),
    ('Belleza y bienestar', 'Estética, barbería, masajes y cuidado personal.'),
    ('Educación y clases', 'Clases particulares, cursos y tutorías.'),
    ('Transporte y entregas', 'Traslados, delivery y encomiendas.'),
    ('Salud', 'Servicios médicos, terapéuticos y de cuidado.'),
    ('Hogar', 'Limpieza, jardinería y servicios para el hogar.'),
    ('Tecnología', 'Soporte técnico, desarrollo y servicios digitales.'),
    ('Eventos', 'Organización, fotografía y servicios para eventos.'),
    ('Otros', 'Servicios que no pertenecen a otra categoría.'),
)


def seed_categories(apps, schema_editor):
    Categoria = apps.get_model('store', 'Categoria')

    def ensure(name, description, tipo, es_comida=False):
        categoria = Categoria.objects.filter(
            nombre__iexact=name,
            tipo=tipo,
        ).first()
        if categoria is None:
            Categoria.objects.create(
                nombre=name,
                descripcion=description,
                tipo=tipo,
                es_comida=es_comida,
            )
        else:
            fields_to_update = []
            if es_comida and not categoria.es_comida:
                categoria.es_comida = True
                fields_to_update.append('es_comida')
            if not categoria.descripcion:
                categoria.descripcion = description
                fields_to_update.append('descripcion')
            if fields_to_update:
                categoria.save(update_fields=fields_to_update)

    for name, description, es_comida in PRODUCT_CATEGORIES:
        ensure(name, description, 'PRODUCTO', es_comida)
    for name, description in SERVICE_CATEGORIES:
        ensure(name, description, 'SERVICIO')


class Migration(migrations.Migration):
    dependencies = [
        ('store', '0034_servicerequest_pago_delivery'),
    ]

    operations = [
        migrations.RunPython(seed_categories, migrations.RunPython.noop),
    ]
