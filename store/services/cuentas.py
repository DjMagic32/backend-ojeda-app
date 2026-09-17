"""Cuentas por cobrar: crédito a clientes con diferencial cambiario realizado.

El saldo vive en USD (moneda funcional). Cada abono se liquida en bolívares a la
tasa vigente al momento del pago; la diferencia entre la tasa de emisión y la de
liquidación se registra como ganancia o pérdida cambiaria en VES, sin afectar el
saldo en USD de la cuenta (ΔC = monto_usd_abonado · (tasa_liquidación − tasa_emisión)).
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import connection, transaction

from store.models import AbonoCuentaPorCobrar, CuentaPorCobrar, OperacionCuentaPorCobrar, TasaCambio


def cuentas_por_cobrar_disponible():
    with connection.cursor() as cursor:
        tablas = set(connection.introspection.table_names(cursor))
    return all(
        model._meta.db_table in tablas
        for model in (CuentaPorCobrar, AbonoCuentaPorCobrar, OperacionCuentaPorCobrar)
    )


def resumen_cuenta(cuenta):
    return {
        'id': cuenta.pk, 'cliente_nombre': cuenta.cliente_nombre, 'cliente_telefono': cuenta.cliente_telefono,
        'order_id': cuenta.order_id, 'monto_usd': str(cuenta.monto_usd), 'saldo_usd': str(cuenta.saldo_usd),
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
        cuenta = CuentaPorCobrar.objects.select_for_update().get(pk=cuenta_id, tienda_id=tienda_id)
    except CuentaPorCobrar.DoesNotExist:
        raise ValidationError('La cuenta por cobrar no está disponible para tu tienda.')
    return cuenta


def crear_cuenta_por_cobrar(tienda, usuario, datos):
    with transaction.atomic():
        tasa = TasaCambio.vigente()
        if tasa is None:
            raise ValidationError('No hay una tasa de cambio registrada. Registra la tasa BCV antes de abrir crédito.')
        monto = datos['monto_usd']
        cuenta = CuentaPorCobrar.objects.create(
            tienda_id=tienda.pk, cliente_nombre=datos['cliente_nombre'],
            cliente_telefono=datos.get('cliente_telefono', ''), order_id=datos.get('order_id'),
            monto_usd=monto, saldo_usd=monto, tasa_emision=tasa.valor_bs,
            vencimiento=datos.get('vencimiento'), notas=datos.get('notas', ''), creado_por=usuario.pk,
        )
        return {'cuenta': resumen_cuenta(cuenta)}


def registrar_abono(tienda, usuario, datos):
    with transaction.atomic():
        cuenta = bloquear_cuenta(tienda.pk, datos['cuenta_id'])
        if cuenta.estado in (CuentaPorCobrar.ESTADO_PAGADA, CuentaPorCobrar.ESTADO_ANULADA):
            raise ValidationError('Esta cuenta por cobrar ya no admite abonos.')
        monto_usd = datos['monto_usd']
        if monto_usd > cuenta.saldo_usd:
            raise ValidationError('El abono no puede superar el saldo pendiente de la cuenta.')
        tasa = TasaCambio.vigente()
        if tasa is None:
            raise ValidationError('No hay una tasa de cambio registrada para liquidar el abono.')
        tasa_liquidacion = tasa.valor_bs
        diferencial = (monto_usd * (tasa_liquidacion - cuenta.tasa_emision)).quantize(Decimal('0.01'))
        abono = AbonoCuentaPorCobrar.objects.create(
            cuenta=cuenta, monto_usd=monto_usd, tasa_liquidacion=tasa_liquidacion,
            monto_ves_equivalente=(monto_usd * tasa_liquidacion).quantize(Decimal('0.01')),
            diferencial_cambiario_ves=diferencial,
            medio_pago=datos.get('medio_pago', 'efectivo'), registrado_por=usuario.pk,
        )
        cuenta.saldo_usd = cuenta.saldo_usd - monto_usd
        cuenta.estado = CuentaPorCobrar.ESTADO_PAGADA if cuenta.saldo_usd == 0 else CuentaPorCobrar.ESTADO_PARCIAL
        cuenta.save(update_fields=['saldo_usd', 'estado', 'actualizado'])
        return {'cuenta': resumen_cuenta(cuenta), 'abono': resumen_abono(abono)}


def anular_cuenta(tienda, usuario, cuenta_id, motivo=''):
    with transaction.atomic():
        cuenta = bloquear_cuenta(tienda.pk, cuenta_id)
        if cuenta.estado in (CuentaPorCobrar.ESTADO_PAGADA, CuentaPorCobrar.ESTADO_ANULADA):
            raise ValidationError('Esta cuenta por cobrar ya no se puede anular.')
        if cuenta.saldo_usd != cuenta.monto_usd:
            raise ValidationError('Solo se puede anular una cuenta sin abonos registrados.')
        cuenta.estado = CuentaPorCobrar.ESTADO_ANULADA
        if motivo:
            cuenta.notas = (cuenta.notas + '\n' if cuenta.notas else '') + f'Anulada: {motivo}'
        cuenta.save(update_fields=['estado', 'notas', 'actualizado'])
        return {'cuenta': resumen_cuenta(cuenta)}
