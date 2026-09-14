"""Gastos operativos: registro plano de egresos por tipo, categoría y sucursal."""
from django.core.exceptions import ValidationError
from django.db import connection, transaction

from store.models import Gasto, OperacionGasto, Sucursal, TasaCambio


def gastos_disponible():
    with connection.cursor() as cursor:
        tablas = set(connection.introspection.table_names(cursor))
    return all(model._meta.db_table in tablas for model in (Gasto, OperacionGasto))


def resumen_gasto(gasto):
    return {
        'id': gasto.pk, 'sucursal_id': gasto.sucursal_id, 'tipo': gasto.tipo,
        'categoria': gasto.categoria, 'descripcion': gasto.descripcion,
        'monto': str(gasto.monto), 'moneda': gasto.moneda,
        'tasa_aplicada': str(gasto.tasa_aplicada) if gasto.tasa_aplicada is not None else None,
        'anulado': gasto.anulado, 'notas': gasto.notas, 'creado': gasto.creado.isoformat(),
    }


def crear_gasto(tienda, usuario, datos):
    with transaction.atomic():
        sucursal_id = datos.get('sucursal_id')
        if sucursal_id is not None:
            existe = Sucursal.objects.filter(pk=sucursal_id, negocio__tienda=tienda, activo=True).exists()
            if not existe:
                raise ValidationError('Selecciona una sucursal activa de tu negocio.')
        tasa = TasaCambio.vigente()
        gasto = Gasto.objects.create(
            tienda_id=tienda.pk, sucursal_id=sucursal_id, tipo=datos['tipo'],
            categoria=datos['categoria'], descripcion=datos.get('descripcion', ''),
            monto=datos['monto'], moneda=datos['moneda'],
            tasa_aplicada=tasa.valor_bs if tasa else None,
            registrado_por=usuario.pk,
        )
        return {'gasto': resumen_gasto(gasto)}


def anular_gasto(tienda, usuario, gasto_id, motivo=''):
    with transaction.atomic():
        try:
            gasto = Gasto.objects.select_for_update().get(pk=gasto_id, tienda_id=tienda.pk)
        except Gasto.DoesNotExist:
            raise ValidationError('El gasto no está disponible para tu tienda.')
        if gasto.anulado:
            raise ValidationError('Este gasto ya está anulado.')
        gasto.anulado = True
        if motivo:
            gasto.notas = (gasto.notas + '\n' if gasto.notas else '') + f'Anulado: {motivo}'
        gasto.save(update_fields=['anulado', 'notas'])
        return {'gasto': resumen_gasto(gasto)}
