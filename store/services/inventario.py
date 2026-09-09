from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from store.models import (
    Almacen,
    InventarioAlmacen,
    MovimientoStock,
    ProductoTienda,
    TransferenciaInventario,
)


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


def transferir_stock(producto, almacen_origen, almacen_destino, cantidad, usuario, notas=''):
    """Mueve existencias entre almacenes en una única transacción."""
    if cantidad <= 0:
        raise ValidationError('La cantidad a transferir debe ser mayor que cero.')
    if almacen_origen.pk == almacen_destino.pk:
        raise ValidationError('El almacén de origen y destino deben ser diferentes.')

    with transaction.atomic():
        producto = ProductoTienda.objects.select_for_update().get(pk=producto.pk)
        if producto.tipo == ProductoTienda.TIPO_SERVICIO or producto.stock is None:
            raise ValidationError('Los servicios y productos sin control de stock no se pueden transferir.')

        almacenes = {
            almacen.pk: almacen
            for almacen in Almacen.objects.select_for_update()
            .select_related('sucursal__negocio')
            .filter(pk__in=[almacen_origen.pk, almacen_destino.pk])
            .order_by('pk')
        }
        if len(almacenes) != 2:
            raise ValidationError('Los almacenes indicados no existen.')

        origen = almacenes[almacen_origen.pk]
        destino = almacenes[almacen_destino.pk]
        if not origen.activo or not destino.activo or not origen.sucursal.activo or not destino.sucursal.activo:
            raise ValidationError('Solo puedes transferir hacia y desde almacenes activos.')
        if origen.sucursal.negocio_id != destino.sucursal.negocio_id:
            raise ValidationError('Los almacenes deben pertenecer al mismo negocio.')
        if origen.sucursal.negocio.tienda_id != producto.tienda_id:
            raise ValidationError('El producto y los almacenes deben pertenecer al mismo negocio.')

        balances = list(
            InventarioAlmacen.objects.select_for_update()
            .filter(producto=producto, almacen_id__in=[origen.pk, destino.pk])
            .order_by('almacen_id')
        )
        balances_by_warehouse = {balance.almacen_id: balance for balance in balances}

        # Si una instalación anterior todavía no tiene detalle, su stock total
        # se considera ubicado en el origen de la primera transferencia.
        source_balance = balances_by_warehouse.get(origen.pk)
        if source_balance is None:
            initial_quantity = producto.stock if not balances else 0
            source_balance = InventarioAlmacen.objects.create(
                producto=producto,
                almacen=origen,
                cantidad=initial_quantity,
            )

        destination_balance = balances_by_warehouse.get(destino.pk)
        if destination_balance is None:
            destination_balance = InventarioAlmacen.objects.create(
                producto=producto,
                almacen=destino,
                cantidad=0,
            )

        if source_balance.cantidad < cantidad:
            raise ValidationError(
                f"Stock insuficiente de '{producto.nombre}' en '{origen.nombre}': "
                f"quedan {source_balance.cantidad} unidad(es)."
            )

        transferencia = TransferenciaInventario.objects.create(
            producto=producto,
            almacen_origen=origen,
            almacen_destino=destino,
            cantidad=cantidad,
            creado_por=usuario,
            notas=(notas or '').strip(),
        )

        source_balance.cantidad -= cantidad
        source_balance.save(update_fields=['cantidad', 'actualizado'])
        destination_balance.cantidad += cantidad
        destination_balance.save(update_fields=['cantidad', 'actualizado'])

        total_stock = (
            InventarioAlmacen.objects
            .filter(producto=producto)
            .aggregate(total=Sum('cantidad'))['total']
            or 0
        )
        producto.stock = total_stock
        producto.save(update_fields=['stock'])

        MovimientoStock.objects.create(
            producto=producto,
            almacen=origen,
            transferencia=transferencia,
            tipo=MovimientoStock.TIPO_TRANSFERENCIA,
            cantidad=-cantidad,
            stock_resultante=total_stock,
            stock_almacen_resultante=source_balance.cantidad,
            origen=MovimientoStock.ORIGEN_TRANSFERENCIA,
        )
        MovimientoStock.objects.create(
            producto=producto,
            almacen=destino,
            transferencia=transferencia,
            tipo=MovimientoStock.TIPO_TRANSFERENCIA,
            cantidad=cantidad,
            stock_resultante=total_stock,
            stock_almacen_resultante=destination_balance.cantidad,
            origen=MovimientoStock.ORIGEN_TRANSFERENCIA,
        )

        return transferencia
