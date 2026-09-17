from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.db.models import Sum
from django.utils import timezone

from store.models import Almacen, SesionCaja, MovimientoCaja, OperacionCaja
from store.services.ventas import registrar_venta_presencial


def caja_disponible():
    with connection.cursor() as cursor:
        tablas = set(connection.introspection.table_names(cursor))
    return all(model._meta.db_table in tablas for model in (SesionCaja, MovimientoCaja, OperacionCaja))


def calcular_saldos(fondo_usd, fondo_ves, grupos):
    efectivo = {'USD': Decimal(fondo_usd), 'VES': Decimal(fondo_ves)}
    ventas = {'USD': {}, 'VES': {}}
    for grupo in grupos:
        moneda, tipo, medio = grupo['moneda'], grupo['tipo'], grupo['medio_pago']
        monto = Decimal(grupo['total'])
        if tipo == 'venta':
            ventas[moneda][medio] = ventas[moneda].get(medio, Decimal('0')) + monto
        if medio == 'efectivo':
            efectivo[moneda] += -monto if tipo == 'retiro' else monto
    return efectivo, ventas


def resumen_caja(sesion):
    grupos = sesion.movimientos.values('moneda', 'tipo', 'medio_pago').annotate(total=Sum('monto'))
    saldos, ventas = calcular_saldos(sesion.fondo_usd, sesion.fondo_ves, grupos)
    if not sesion.abierta:
        saldos = {'USD': sesion.esperado_usd, 'VES': sesion.esperado_ves}
    return {
        'id': sesion.pk, 'almacen_id': sesion.almacen_id, 'almacen_nombre': sesion.almacen_nombre,
        'sucursal_nombre': sesion.sucursal_nombre, 'abierta': sesion.abierta,
        'abierto_por': sesion.abierto_por, 'cerrado_por': sesion.cerrado_por,
        'abierto': sesion.abierto.isoformat(), 'cerrado': sesion.cerrado.isoformat() if sesion.cerrado else None,
        'notas_cierre': sesion.notas_cierre,
        'fondos': {'USD': str(sesion.fondo_usd), 'VES': str(sesion.fondo_ves)},
        'esperado': {moneda: str(monto) for moneda, monto in saldos.items()},
        'contado': None if sesion.abierta else {'USD': str(sesion.contado_usd), 'VES': str(sesion.contado_ves)},
        'diferencia': None if sesion.abierta else {
            'USD': str(sesion.contado_usd - saldos['USD']), 'VES': str(sesion.contado_ves - saldos['VES']),
        },
        'ventas_por_medio': {moneda: {medio: str(monto) for medio, monto in medios.items()} for moneda, medios in ventas.items()},
    }


def bloquear_sesion(tienda_id, sesion_id):
    try:
        sesion = SesionCaja.objects.select_for_update().get(pk=sesion_id, tienda_id=tienda_id)
    except SesionCaja.DoesNotExist:
        raise ValidationError('La sesión de caja no está disponible para tu tienda.')
    if not sesion.abierta:
        raise ValidationError('La sesión de caja ya está cerrada.')
    return sesion


def ejecutar_operacion_caja(tienda, usuario, datos):
    with transaction.atomic():
        accion = datos['accion']
        if accion == 'abrir':
            almacen = Almacen.objects.select_for_update().select_related('sucursal__negocio').filter(
                pk=datos['almacen_id'], sucursal__negocio__tienda=tienda, activo=True, sucursal__activo=True,
            ).first()
            if almacen is None:
                raise ValidationError('Selecciona un almacén activo de tu tienda.')
            if SesionCaja.objects.filter(tienda_id=tienda.pk, almacen_id=almacen.pk, abierta=True).exists():
                raise ValidationError('Este almacén ya tiene una sesión de caja abierta.')
            sesion = SesionCaja.objects.create(
                tienda_id=tienda.pk, almacen_id=almacen.pk, almacen_nombre=almacen.nombre,
                sucursal_nombre=almacen.sucursal.nombre, abierto_por=usuario.pk,
                fondo_usd=datos['fondo_usd'], fondo_ves=datos['fondo_ves'],
            )
        else:
            sesion = bloquear_sesion(tienda.pk, datos['sesion_id'])
            if accion in ('entrada', 'retiro'):
                resumen = resumen_caja(sesion)
                if accion == 'retiro' and datos['monto'] > Decimal(resumen['esperado'][datos['moneda']]):
                    raise ValidationError('El retiro supera el efectivo disponible en esa moneda.')
                MovimientoCaja.objects.create(
                    sesion=sesion, tipo=accion, moneda=datos['moneda'], monto=datos['monto'],
                    medio_pago='efectivo', motivo=datos['motivo'], usuario_id=usuario.pk,
                )
            elif accion == 'cerrar':
                resumen = resumen_caja(sesion)
                sesion.esperado_usd = Decimal(resumen['esperado']['USD'])
                sesion.esperado_ves = Decimal(resumen['esperado']['VES'])
                sesion.contado_usd = datos['contado_usd']
                sesion.contado_ves = datos['contado_ves']
                sesion.notas_cierre = datos.get('motivo', '')
                sesion.cerrado_por = usuario.pk
                sesion.cerrado = timezone.now()
                sesion.abierta = False
                sesion.save(update_fields=['esperado_usd', 'esperado_ves', 'contado_usd', 'contado_ves',
                                          'notas_cierre', 'cerrado_por', 'cerrado', 'abierta'])
            else:
                raise ValidationError('La operación de caja no es válida.')
        return {'sesion': resumen_caja(sesion)}


def registrar_venta_en_caja(tienda, usuario, datos):
    with transaction.atomic():
        sesion = bloquear_sesion(tienda.pk, datos['sesion_caja_id'])
        if sesion.almacen_id != datos.get('almacen_id'):
            raise ValidationError('El almacén de la venta debe coincidir con el de la caja.')
        order, movimientos = registrar_venta_presencial(
            tienda, usuario, datos['items'], sesion.almacen_id, datos.get('notas', ''),
        )
        if order.total < 0:
            raise ValidationError('El importe de una venta de caja no puede ser negativo.')
        MovimientoCaja.objects.create(
            sesion=sesion, tipo='venta', moneda=order.moneda, monto=order.total,
            medio_pago=datos['medio_pago'], usuario_id=usuario.pk, order_id=order.pk,
        )
        return order, movimientos
