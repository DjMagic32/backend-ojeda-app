"""Serializa confirmación/cancelación por tienda y clave dentro de la misma transacción."""
import hashlib
import json

from django.db import connection, transaction

from store.models import OperacionVentaPresencial


class ConflictoOperacion(Exception):
    pass


def idempotencia_disponible():
    # No consultar el modelo hasta que exista su tabla: un despliegue sin migrate
    # debe responder 503 en el nuevo endpoint y conservar las rutas anteriores.
    with connection.cursor() as cursor:
        return OperacionVentaPresencial._meta.db_table in connection.introspection.table_names(cursor)


def huella_venta(items, almacen_id=None, notas=''):
    # El orden de líneas es parte del ticket original, incluidas líneas repetidas.
    datos = {'items': items, 'almacen_id': almacen_id, 'notas': notas or ''}
    return hashlib.sha256(json.dumps(datos, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def confirmar_operacion(tienda_id, clave, huella, crear_venta):
    with transaction.atomic():
        operacion, _ = OperacionVentaPresencial.objects.get_or_create(
            tienda_id=tienda_id, clave=clave, defaults={'huella': huella},
        )
        operacion = OperacionVentaPresencial.objects.select_for_update().get(pk=operacion.pk)
        if operacion.cancelada:
            raise ConflictoOperacion('Esta operación fue cancelada. No se registrará otra venta con esa clave.')
        if operacion.huella != huella:
            raise ConflictoOperacion('La clave ya pertenece a un ticket diferente. Recupera la operación original.')
        if operacion.respuesta is not None:
            return operacion.respuesta, True
        # Incluye orden, líneas, movimientos y comprobante en el mismo commit.
        respuesta = crear_venta()
        operacion.respuesta = respuesta
        operacion.save(update_fields=['respuesta'])
        return respuesta, False


def cancelar_operacion(tienda_id, clave):
    with transaction.atomic():
        operacion, _ = OperacionVentaPresencial.objects.get_or_create(tienda_id=tienda_id, clave=clave)
        operacion = OperacionVentaPresencial.objects.select_for_update().get(pk=operacion.pk)
        if operacion.respuesta is not None:
            return operacion.respuesta
        # La marca se conserva: un POST retrasado no puede cobrar después de cancelar.
        operacion.cancelada = True
        operacion.save(update_fields=['cancelada'])
        return None
