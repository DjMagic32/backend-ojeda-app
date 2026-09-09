from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from store.models import Almacen, InventarioAlmacen, MovimientoStock, ProductoTienda


def obtener_almacen_principal(producto):
    """Devuelve el almacén principal de la tienda, si ya existe.

    La ausencia del almacén mantiene el comportamiento legado basado solo en
    ``ProductoTienda.stock``. Esto permite desplegar la migración gradualmente.
    """
    return (
        Almacen.objects.filter(
            sucursal__negocio__tienda_id=producto.tienda_id,
            sucursal__activo=True,
            activo=True,
            codigo='PRINCIPAL',
        )
        .order_by('id')
        .first()
    )


def registrar_movimiento(producto, tipo, delta, origen, order=None, almacen=None):
    """Registra un movimiento y conserva el stock agregado por compatibilidad.

    Cuando la tienda tiene estructura administrativa, las operaciones antiguas
    que no envían almacén se registran automáticamente en el principal. Así,
    las ventas online, presenciales y ajustes existentes no quedan separadas
    del nuevo inventario por almacén.
    """
    with transaction.atomic():
        producto = ProductoTienda.objects.select_for_update().get(pk=producto.pk)

        if producto.tipo == ProductoTienda.TIPO_SERVICIO or producto.stock is None:
            return MovimientoStock.objects.create(
                producto=producto,
                tipo=tipo,
                cantidad=delta,
                stock_resultante=None,
                origen=origen,
                order=order,
            )

        almacen = almacen or obtener_almacen_principal(producto)
        if almacen is not None:
            if almacen.sucursal.negocio.tienda_id != producto.tienda_id:
                raise ValidationError('El almacén no pertenece a la tienda del producto.')

            existencias = InventarioAlmacen.objects.filter(producto=producto)
            tiene_existencias = existencias.exists()
            existencia, _ = InventarioAlmacen.objects.get_or_create(
                producto=producto,
                almacen=almacen,
                defaults={
                    # Si se creó un almacén después del producto y aún no hay
                    # detalle, conservamos el total legado en ese primer almacén.
                    'cantidad': producto.stock if not tiene_existencias else 0,
                },
            )
            existencia = InventarioAlmacen.objects.select_for_update().get(pk=existencia.pk)
            nueva_existencia = existencia.cantidad + delta
            if nueva_existencia < 0:
                raise ValidationError(
                    f"Stock insuficiente de '{producto.nombre}' en '{almacen.nombre}': "
                    f"quedan {existencia.cantidad} unidad(es)."
                )

            existencia.cantidad = nueva_existencia
            existencia.save(update_fields=['cantidad', 'actualizado'])
            nuevo_stock = (
                InventarioAlmacen.objects
                .filter(producto=producto)
                .aggregate(total=Sum('cantidad'))['total']
                or 0
            )
            producto.stock = nuevo_stock
            producto.save(update_fields=['stock'])

            return MovimientoStock.objects.create(
                producto=producto,
                almacen=almacen,
                tipo=tipo,
                cantidad=delta,
                stock_resultante=nuevo_stock,
                stock_almacen_resultante=nueva_existencia,
                origen=origen,
                order=order,
            )

        nuevo_stock = producto.stock + delta
        if nuevo_stock < 0:
            raise ValidationError(
                f"Stock insuficiente de '{producto.nombre}': quedan {producto.stock} unidad(es)."
            )

        producto.stock = nuevo_stock
        producto.save(update_fields=['stock'])

        return MovimientoStock.objects.create(
            producto=producto,
            tipo=tipo,
            cantidad=delta,
            stock_resultante=nuevo_stock,
            stock_almacen_resultante=None,
            origen=origen,
            order=order,
        )
