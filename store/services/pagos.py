"""Cuentas por pagar: deuda con proveedores con diferencial cambiario realizado.

Simétrico a ``store/services/cuentas.py`` (cuentas por cobrar), con el signo del
diferencial invertido: si la tasa sube entre la emisión de la deuda y su pago,
liquidar el mismo monto en USD cuesta más bolívares, lo que es una PÉRDIDA
cambiaria para el negocio (ΔC = monto_usd_abonado · (tasa_emisión − tasa_liquidación);
negativo = pérdida cuando la tasa subió, positivo = ganancia cuando bajó).
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import connection, transaction

from store.models import AbonoCuentaPorPagar, CuentaPorPagar, OperacionCuentaPorPagar, TasaCambio


def cuentas_por_pagar_disponible():
    with connection.cursor() as cursor:
        tablas = set(connection.introspection.table_names(cursor))
    return all(
        model._meta.db_table in tablas
        for model in (CuentaPorPagar, AbonoCuentaPorPagar, OperacionCuentaPorPagar)
    )


def resumen_cuenta(cuenta):
    return {
        'id': cuenta.pk, 'proveedor_nombre': cuenta.proveedor_nombre,
        'proveedor_telefono': cuenta.proveedor_telefono,
        'monto_usd': str(cuenta.monto_usd), 'saldo_usd': str(cuenta.saldo_usd),
        'tasa_emision': str(cuenta.tasa_emision), 'estado': cuenta.estado,
        'vencimiento': cuenta.vencimiento.isoformat() if cuenta.vencimiento else None,
        'notas': cuenta.notas, 'creado': cuenta.creado.isoformat(),
    }


def resumen_abono(abono):
    return {
        'id': abono.pk, 'cuenta_id': abono.cuenta_id, 'monto_usd': str(abono.monto_usd),
        'tasa_liquidacion': str(abono.tasa_liquidacion),
        'monto_ves_equivalente': str(abono.monto_ves_equivalente),
        'diferencial_cambiario_ves': str(abono.diferencial_cambiario_ves),
        'medio_pago': abono.medio_pago, 'creado': abono.creado.isoformat(),
    }


def bloquear_cuenta(tienda_id, cuenta_id):
    try:
        cuenta = CuentaPorPagar.objects.select_for_update().get(pk=cuenta_id, tienda_id=tienda_id)
    except CuentaPorPagar.DoesNotExist:
        raise ValidationError('La cuenta por pagar no está disponible para tu tienda.')
    return cuenta


def crear_cuenta_por_pagar(tienda, usuario, datos):
    with transaction.atomic():
        tasa = TasaCambio.vigente()
        if tasa is None:
            raise ValidationError('No hay una tasa de cambio registrada. Registra la tasa BCV antes de registrar deuda.')
        monto = datos['monto_usd']
        cuenta = CuentaPorPagar.objects.create(
            tienda_id=tienda.pk, proveedor_nombre=datos['proveedor_nombre'],
            proveedor_telefono=datos.get('proveedor_telefono', ''),
            monto_usd=monto, saldo_usd=monto, tasa_emision=tasa.valor_bs,
            vencimiento=datos.get('vencimiento'), notas=datos.get('notas', ''), creado_por=usuario.pk,
        )
        return {'cuenta': resumen_cuenta(cuenta)}


def registrar_abono(tienda, usuario, datos):
    with transaction.atomic():
        cuenta = bloquear_cuenta(tienda.pk, datos['cuenta_id'])
        if cuenta.estado in (CuentaPorPagar.ESTADO_PAGADA, CuentaPorPagar.ESTADO_ANULADA):
            raise ValidationError('Esta cuenta por pagar ya no admite abonos.')
        monto_usd = datos['monto_usd']
        if monto_usd > cuenta.saldo_usd:
            raise ValidationError('El abono no puede superar el saldo pendiente de la cuenta.')
        tasa = TasaCambio.vigente()
        if tasa is None:
            raise ValidationError('No hay una tasa de cambio registrada para liquidar el abono.')
        tasa_liquidacion = tasa.valor_bs
        diferencial = (monto_usd * (cuenta.tasa_emision - tasa_liquidacion)).quantize(Decimal('0.01'))
        abono = AbonoCuentaPorPagar.objects.create(
            cuenta=cuenta, monto_usd=monto_usd, tasa_liquidacion=tasa_liquidacion,
            monto_ves_equivalente=(monto_usd * tasa_liquidacion).quantize(Decimal('0.01')),
            diferencial_cambiario_ves=diferencial,
            medio_pago=datos.get('medio_pago', 'efectivo'), registrado_por=usuario.pk,
        )
        cuenta.saldo_usd = cuenta.saldo_usd - monto_usd
        cuenta.estado = CuentaPorPagar.ESTADO_PAGADA if cuenta.saldo_usd == 0 else CuentaPorPagar.ESTADO_PARCIAL
        cuenta.save(update_fields=['saldo_usd', 'estado', 'actualizado'])
        return {'cuenta': resumen_cuenta(cuenta), 'abono': resumen_abono(abono)}


def anular_cuenta(tienda, usuario, cuenta_id, motivo=''):
    with transaction.atomic():
        cuenta = bloquear_cuenta(tienda.pk, cuenta_id)
        if cuenta.estado in (CuentaPorPagar.ESTADO_PAGADA, CuentaPorPagar.ESTADO_ANULADA):
            raise ValidationError('Esta cuenta por pagar ya no se puede anular.')
        if cuenta.saldo_usd != cuenta.monto_usd:
            raise ValidationError('Solo se puede anular una cuenta sin abonos registrados.')
        cuenta.estado = CuentaPorPagar.ESTADO_ANULADA
        if motivo:
            cuenta.notas = (cuenta.notas + '\n' if cuenta.notas else '') + f'Anulada: {motivo}'
        cuenta.save(update_fields=['estado', 'notas', 'actualizado'])
        return {'cuenta': resumen_cuenta(cuenta)}
