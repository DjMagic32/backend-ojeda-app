from django.db import migrations


def crear_items_desde_ordenes(apps, schema_editor):
    StoreOrder = apps.get_model('store', 'StoreOrder')
    StoreOrderItem = apps.get_model('store', 'StoreOrderItem')
    items = [
        StoreOrderItem(
            order_id=order.id,
            producto_id=order.producto_id,
            cantidad=order.cantidad,
            precio_unitario=order.precio_unitario,
            subtotal=order.precio_unitario * order.cantidad,
        )
        for order in StoreOrder.objects.filter(items__isnull=True)
    ]
    StoreOrderItem.objects.bulk_create(items)


def eliminar_items(apps, schema_editor):
    StoreOrderItem = apps.get_model('store', 'StoreOrderItem')
    StoreOrderItem.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0021_storeorderitem'),
    ]

    operations = [
        migrations.RunPython(crear_items_desde_ordenes, eliminar_items),
    ]
