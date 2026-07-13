from django.core.exceptions import ValidationError
from django.db import transaction

from store.models import MovimientoStock, ProductoTienda


def registrar_movimiento(producto, tipo, delta, origen, order=None):
    """Registra un movimiento de stock y actualiza el producto de forma atómica."""
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
            origen=origen,
            order=order,
        )
