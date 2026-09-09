from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from store.models import (
    Almacen,
    InventarioAlmacen,
    MovimientoStock,
    ProductoTienda,
    ReservaInventario,
    StoreOrder,
    StoreOrderItem,
    TransferenciaInventario,
)


RESERVA_DURACION = timedelta(minutes=30)


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


def _cantidad_comprometida_sin_reserva(producto, order=None):
    """Cuenta órdenes antiguas que aún no tienen filas de reserva.

    Antes de existir ``ReservaInventario`` las órdenes pendientes se protegían
    sólo con una consulta agregada. Se mantienen en el cálculo para que el
    despliegue sea gradual y no permita sobre vender pedidos creados antes de
    esta migración.
    """
    estados_activos = [StoreOrder.ESTADO_PENDIENTE, StoreOrder.ESTADO_EN_CURSO]
    items = StoreOrderItem.objects.filter(
        producto=producto,
        order__canal=StoreOrder.CANAL_ONLINE,
        order__estado__in=estados_activos,
        order__reservas__isnull=True,
    )
    if order is not None:
        items = items.exclude(order_id=order.pk)
    cantidad_items = items.aggregate(total=Sum('cantidad'))['total'] or 0

    # El endpoint REST antiguo podía crear una orden sin StoreOrderItem.
    orders_without_items = StoreOrder.objects.filter(
        producto=producto,
        canal=StoreOrder.CANAL_ONLINE,
        estado__in=estados_activos,
        items__isnull=True,
    )
    if order is not None:
        orders_without_items = orders_without_items.exclude(pk=order.pk)
    cantidad_ordenes = orders_without_items.aggregate(total=Sum('cantidad'))['total'] or 0
    return cantidad_items + cantidad_ordenes


def _reservar_stock_producto(producto, cantidad, order):
    """Reserva una cantidad distribuyéndola entre almacenes disponibles."""
    if (
        producto.tipo == ProductoTienda.TIPO_SERVICIO
        or producto.stock is None
        or producto.permite_encargo
    ):
        return []

    if cantidad <= 0:
        raise ValidationError('La cantidad a reservar debe ser mayor que cero.')

    producto = ProductoTienda.objects.select_for_update().get(pk=producto.pk)
    ahora = timezone.now()
    ReservaInventario.objects.filter(
        producto=producto,
        estado=ReservaInventario.ESTADO_ACTIVA,
        expira_en__lte=ahora,
    ).update(
        estado=ReservaInventario.ESTADO_EXPIRADA,
        actualizado=ahora,
    )
    if ReservaInventario.objects.filter(
        order=order,
        producto=producto,
        estado=ReservaInventario.ESTADO_ACTIVA,
    ).exists():
        return []

    reservas_por_almacen = {
        row['almacen_id']: row['total']
        for row in ReservaInventario.objects.filter(
            producto=producto,
            estado=ReservaInventario.ESTADO_ACTIVA,
        ).values('almacen_id').annotate(total=Sum('cantidad'))
    }
    legacy_committed = _cantidad_comprometida_sin_reserva(producto, order=order)

    balances = list(
        InventarioAlmacen.objects.select_for_update()
        .select_related('almacen__sucursal')
        .filter(
            producto=producto,
            almacen__activo=True,
            almacen__sucursal__activo=True,
        )
        .order_by('almacen__codigo', 'almacen_id')
    )

    if not balances:
        reserved = sum(reservas_por_almacen.values())
        disponible = max(producto.stock - reserved - legacy_committed, 0)
        if cantidad > disponible:
            raise ValidationError(
                f"Stock insuficiente de '{producto.nombre}': solo quedan "
                f'{disponible} unidad(es) disponibles.'
            )
        return [
            ReservaInventario.objects.create(
                order=order,
                producto=producto,
                cantidad=cantidad,
                expira_en=ahora + RESERVA_DURACION,
            )
        ]

    # Las reservas sin almacén y los pedidos heredados se consideran ocupados
    # primero en el orden determinista de los almacenes.
    bloqueado_sin_almacen = reservas_por_almacen.get(None, 0) + legacy_committed
    capacidades = []
    total_disponible = 0
    for balance in balances:
        capacidad = max(balance.cantidad - reservas_por_almacen.get(balance.almacen_id, 0), 0)
        bloqueado = min(capacidad, bloqueado_sin_almacen)
        bloqueado_sin_almacen -= bloqueado
        disponible = capacidad - bloqueado
        capacidades.append((balance, disponible))
        total_disponible += disponible

    if cantidad > total_disponible:
        raise ValidationError(
            f"Stock insuficiente de '{producto.nombre}': solo quedan "
            f'{total_disponible} unidad(es) disponibles.'
        )

    reservas = []
    restante = cantidad
    for balance, disponible in capacidades:
        if restante <= 0:
            break
        cantidad_almacen = min(restante, disponible)
        if cantidad_almacen <= 0:
            continue
        reservas.append(
            ReservaInventario.objects.create(
                order=order,
                producto=producto,
                almacen=balance.almacen,
                cantidad=cantidad_almacen,
                expira_en=ahora + RESERVA_DURACION,
            )
        )
        restante -= cantidad_almacen
    return reservas


def reservar_stock_orden(order):
    """Crea reservas idempotentes para todos los artículos de una orden online."""
    if order.canal != StoreOrder.CANAL_ONLINE:
        return []

    items = list(order.items.select_related('producto').all())
    if not items:
        items = [order]

    reservas = []
    with transaction.atomic():
        # El orden estable reduce la posibilidad de deadlocks en carritos con
        # varios productos que se procesan simultáneamente.
        items.sort(key=lambda item: item.producto_id)
        for item in items:
            reservas.extend(
                _reservar_stock_producto(
                    producto=item.producto,
                    cantidad=item.cantidad,
                    order=order,
                )
            )
    return reservas


def liberar_reservas_orden(order):
    """Libera las reservas activas cuando una orden se cancela."""
    with transaction.atomic():
        reservas = ReservaInventario.objects.select_for_update().filter(
            order=order,
            estado=ReservaInventario.ESTADO_ACTIVA,
        )
        return reservas.update(
            estado=ReservaInventario.ESTADO_LIBERADA,
            actualizado=timezone.now(),
        )


def consumir_reservas_orden(order):
    """Consume una reserva y descuenta stock exactamente una vez."""
    if order.canal != StoreOrder.CANAL_ONLINE:
        return []

    with transaction.atomic():
        # Serializa dos completados simultáneos de la misma orden antes de
        # comprobar si ya existe el movimiento de salida.
        StoreOrder.objects.select_for_update().get(pk=order.pk)
        if MovimientoStock.objects.filter(order=order).exists():
            return []
        ahora = timezone.now()
        ReservaInventario.objects.filter(
            order=order,
            estado=ReservaInventario.ESTADO_ACTIVA,
            expira_en__lte=ahora,
        ).update(
            estado=ReservaInventario.ESTADO_EXPIRADA,
            actualizado=ahora,
        )
        if ReservaInventario.objects.filter(
            order=order,
            estado=ReservaInventario.ESTADO_EXPIRADA,
        ).exists():
            raise ValidationError(
                'La reserva de inventario de esta orden expiró. Solicita una nueva orden.'
            )
        reservas = list(
            ReservaInventario.objects.select_for_update()
            .select_related('producto', 'almacen')
            .filter(order=order, estado=ReservaInventario.ESTADO_ACTIVA)
            .order_by('producto_id', 'id')
        )
        movimientos = []
        if reservas:
            for reserva in reservas:
                movimientos.append(
                    registrar_movimiento(
                        reserva.producto,
                        MovimientoStock.TIPO_VENTA,
                        -reserva.cantidad,
                        MovimientoStock.ORIGEN_ORDEN_ONLINE,
                        order=order,
                        almacen=reserva.almacen,
                    )
                )
                reserva.estado = ReservaInventario.ESTADO_CONSUMIDA
                reserva.save(update_fields=['estado', 'actualizado'])
            return movimientos

        # Compatibilidad con órdenes creadas antes de la migración. El nuevo
        # flujo siempre entra por reservas; este fallback evita romperlas.
        items = list(order.items.select_related('producto').all())
        if not items:
            items = [order]
        for item in items:
            producto = item.producto
            if producto.tipo == ProductoTienda.TIPO_SERVICIO or producto.stock is None:
                continue
            delta = -min(item.cantidad, producto.stock)
            if delta == 0:
                continue
            movimientos.append(
                registrar_movimiento(
                    producto,
                    MovimientoStock.TIPO_VENTA,
                    delta,
                    MovimientoStock.ORIGEN_ORDEN_ONLINE,
                    order=order,
                )
            )
        return movimientos
