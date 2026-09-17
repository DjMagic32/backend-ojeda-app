"""Pruebas de paginación con un doble de consulta; no ejecutan Django ni SQL."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest

from store.services.historial import consultar_movimientos


class Consulta(list):
    def select_related(self, *args):
        return self

    def filter(self, **filters):
        def matches(row):
            for name, expected in filters.items():
                field, _, op = name.partition('__')
                actual = getattr(row, field)
                if op == 'lt' and not actual < expected:
                    return False
                if op == 'gte' and not actual >= expected:
                    return False
                if not op and actual != expected:
                    return False
            return True
        return Consulta(row for row in self if matches(row))

    def order_by(self, *fields):
        rows = self
        for field in reversed(fields):
            rows = sorted(rows, key=lambda row: getattr(row, field.lstrip('-')),
                          reverse=field.startswith('-'))
        return Consulta(rows)


class HistorialServiceTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)
        self.rows = Consulta()
        self.product = SimpleNamespace(movimientos_stock=self.rows)

    def add(self, identifier, warehouse=1, origin='ajuste_manual', days=0):
        row = SimpleNamespace(id=identifier, almacen_id=warehouse, origen=origin,
                              creado=self.now - timedelta(days=days))
        self.rows.append(row)
        return row

    def page(self, **filters):
        return consultar_movimientos(self.product, {'paginado': True, **filters}, self.now)

    def test_recupera_mas_de_50_sin_repetir_ante_nueva_entrada(self):
        for identifier in range(1, 126):
            self.add(identifier)
        first, cursor = self.page()
        self.assertEqual(cursor, 76)
        self.add(126)
        second, cursor = self.page(antes_de=cursor)
        self.assertEqual(cursor, 26)
        third, cursor = self.page(antes_de=cursor)
        self.assertIsNone(cursor)
        self.assertEqual([row.id for row in first + second + third], list(range(125, 0, -1)))

    def test_50_exactos_no_ofrece_pagina_vacia(self):
        for identifier in range(1, 51):
            self.add(identifier)
        rows, cursor = self.page()
        self.assertEqual(len(rows), 50)
        self.assertIsNone(cursor)

    def test_51_conserva_ultimo_movimiento(self):
        for identifier in range(1, 52):
            self.add(identifier)
        _, cursor = self.page()
        self.assertEqual(cursor, 2)
        rows, cursor = self.page(antes_de=cursor)
        self.assertEqual([row.id for row in rows], [1])
        self.assertIsNone(cursor)

    def test_filtros_combinados_y_limite_de_fecha_inclusivo(self):
        self.add(1, days=7)
        self.add(2, days=8)
        self.add(3, warehouse=2)
        self.add(4, origin='transferencia')
        rows, _ = self.page(almacen_id=1, origen='ajuste_manual', dias=7)
        self.assertEqual([row.id for row in rows], [1])

    def test_filtra_antes_de_limitar_los_resultados(self):
        self.add(1, warehouse=2)
        for identifier in range(2, 102):
            self.add(identifier)
        rows, cursor = self.page(almacen_id=2)
        self.assertEqual([row.id for row in rows], [1])
        self.assertIsNone(cursor)

    def test_almacen_sin_movimientos_del_producto_no_filtra_datos_ajenos(self):
        self.add(1)
        self.assertEqual(self.page(almacen_id=999), ([], None))

    def test_incluye_legados_sin_almacen_en_consulta_general(self):
        self.add(1, warehouse=None, origin='creacion')
        rows, _ = self.page()
        self.assertEqual([row.id for row in rows], [1])
        self.assertEqual(self.page(almacen_id=1), ([], None))

    def test_cliente_legado_conserva_limite_y_orden_por_fecha(self):
        for identifier in range(1, 61):
            self.add(identifier, days=identifier)
        rows, cursor = consultar_movimientos(self.product, {}, self.now)
        self.assertEqual([row.id for row in rows], list(range(1, 51)))
        self.assertIsNone(cursor)

    def test_historial_vacio(self):
        self.assertEqual(self.page(), ([], None))
