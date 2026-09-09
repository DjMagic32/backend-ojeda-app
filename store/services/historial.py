"""Consulta acotada de movimientos; recibe filtros ya validados y un producto autorizado."""
from datetime import timedelta


def consultar_movimientos(producto, filtros, ahora):
    movimientos = producto.movimientos_stock.select_related('almacen__sucursal')
    if 'almacen_id' in filtros:
        movimientos = movimientos.filter(almacen_id=filtros['almacen_id'])
    if 'origen' in filtros:
        movimientos = movimientos.filter(origen=filtros['origen'])
    if 'dias' in filtros:
        movimientos = movimientos.filter(creado__gte=ahora - timedelta(days=filtros['dias']))
    if 'antes_de' in filtros:
        movimientos = movimientos.filter(id__lt=filtros['antes_de'])

    # El ID da un cursor estable: nuevas entradas no desplazan las páginas anteriores.
    # Se leen 51 filas como máximo, sin contar ni cargar todo el historial.
    paginado = filtros.get('paginado', False)
    orden = ('-id',) if paginado else ('-creado', '-id')
    filas = list(movimientos.order_by(*orden)[:51 if paginado else 50])
    siguiente = filas[49].id if len(filas) > 50 else None
    return filas[:50], siguiente
