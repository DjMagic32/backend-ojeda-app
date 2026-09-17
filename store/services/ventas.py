from django.core.exceptions import ValidationError
from django.db import transaction

from store.models import (
    Almacen, MovimientoStock, ProductoTienda, StoreOrder, StoreOrderItem, TasaCambio,
)
from store.services.inventario import registrar_movimiento


def registrar_venta_presencial(tienda, usuario, items, almacen_id=None, notas=''):
    """Confirma el ticket completo con precios y productos bloqueados.

    El orden de bloqueo es siempre por PK, aunque dos cajas envíen las líneas
    en distinto orden. La transacción incluye orden, líneas y movimientos.
    Los reintentos de red todavía requieren idempotencia persistente.
    """
    with transaction.atomic():
        producto_ids = [item['producto_id'] for item in items]
        if not items or any(item['cantidad'] <= 0 for item in items):
            raise ValidationError('Indica productos y cantidades mayores que cero.')
        productos = {
            p.pk: p for p in ProductoTienda.objects.select_for_update()
            .filter(pk__in=producto_ids, tienda=tienda).order_by('pk')
        }
        if any(pid not in productos for pid in producto_ids):
            raise ValidationError('Algunos productos no pertenecen a tu tienda o no existen.')
        monedas = {producto.moneda for producto in productos.values()}
        if len(monedas) > 1:
            raise ValidationError('No puedes mezclar productos en USD y VES en un mismo ticket.')

        almacen = None
        if almacen_id is not None:
            almacen = Almacen.objects.select_related('sucursal__negocio').filter(
                pk=almacen_id, activo=True, sucursal__activo=True,
                sucursal__negocio__tienda=tienda,
            ).first()
            if almacen is None:
                raise ValidationError('El almacén indicado no está disponible para tu tienda.')

        tasa = TasaCambio.vigente()
        total = sum(productos[item['producto_id']].precio * item['cantidad'] for item in items)
        primer_producto = productos[items[0]['producto_id']]
        order = StoreOrder.objects.create(
            usuario=usuario,
            producto=primer_producto,
            cantidad=items[0]['cantidad'],
            precio_unitario=primer_producto.precio,
            total=total,
            moneda=monedas.pop(),
            tasa_aplicada=tasa.valor_bs if tasa else None,
            estado=StoreOrder.ESTADO_COMPLETADO,
            canal=StoreOrder.CANAL_PRESENCIAL,
            notas=notas or None,
        )
        movimientos = []
        for item in items:
            producto = productos[item['producto_id']]
            StoreOrderItem.objects.create(
                order=order,
                producto=producto,
                cantidad=item['cantidad'],
                precio_unitario=producto.precio,
                subtotal=producto.precio * item['cantidad'],
            )
            movimientos.append(registrar_movimiento(
                producto, MovimientoStock.TIPO_VENTA, -item['cantidad'],
                MovimientoStock.ORIGEN_VENTA_PRESENCIAL, order=order, almacen=almacen,
            ))
        return order, movimientos
