"""Regresiones de venta con dobles de ORM; no acreditan SQL ni concurrencia."""
from decimal import Decimal
import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch


class ValidationError(Exception):
    pass


class VentaPresencialServiceTests(unittest.TestCase):
    def setUp(self):
        modules = {name: ModuleType(name) for name in (
            'django', 'django.core', 'django.core.exceptions', 'django.db',
            'store.models', 'store.services.inventario',
        )}
        modules['django.core.exceptions'].ValidationError = ValidationError
        modules['django.db'].transaction = MagicMock()
        for name in ('Almacen', 'MovimientoStock', 'ProductoTienda', 'StoreOrder',
                     'StoreOrderItem', 'TasaCambio'):
            setattr(modules['store.models'], name, MagicMock())
        modules['store.services.inventario'].registrar_movimiento = MagicMock()
        path = Path(__file__).resolve().parents[1] / 'store/services/ventas.py'
        spec = importlib.util.spec_from_file_location('ventas_bajo_prueba', path)
        self.s = importlib.util.module_from_spec(spec)
        with patch.dict('sys.modules', modules):
            spec.loader.exec_module(self.s)
        self.tienda = SimpleNamespace(pk=1)
        self.user = SimpleNamespace(pk=1)
        self.p1 = SimpleNamespace(pk=1, moneda='USD', precio=Decimal('2.50'))
        self.p2 = SimpleNamespace(pk=2, moneda='USD', precio=Decimal('4.00'))
        self.query = self.s.ProductoTienda.objects.select_for_update.return_value.filter.return_value
        self.query.order_by.return_value = [self.p1, self.p2]
        self.s.TasaCambio.vigente.return_value = SimpleNamespace(valor_bs=Decimal('100.00'))
        self.s.StoreOrder.ESTADO_COMPLETADO = 'completed'
        self.s.StoreOrder.CANAL_PRESENCIAL = 'presencial'
        self.s.MovimientoStock.TIPO_VENTA = 'venta'
        self.s.MovimientoStock.ORIGEN_VENTA_PRESENCIAL = 'venta_presencial'
        self.items = [{'producto_id': 2, 'cantidad': 2}, {'producto_id': 1, 'cantidad': 3}]

    def sale(self, **kwargs):
        return self.s.registrar_venta_presencial(
            self.tienda, self.user, kwargs.pop('items', self.items), **kwargs)

    def test_bloquea_por_pk_y_respeta_orden_del_ticket(self):
        self.sale()
        self.s.ProductoTienda.objects.select_for_update.assert_called_once_with()
        self.query.order_by.assert_called_once_with('pk')
        self.s.ProductoTienda.objects.select_for_update.return_value.filter.assert_called_once_with(
            pk__in=[2, 1], tienda=self.tienda)
        data = self.s.StoreOrder.objects.create.call_args.kwargs
        self.assertIs(data['producto'], self.p2)
        self.assertEqual(data['total'], Decimal('15.50'))
        self.assertEqual((data['estado'], data['canal'], data['tasa_aplicada']),
                         ('completed', 'presencial', Decimal('100.00')))

    def test_movimientos_conservan_cantidad_y_almacen(self):
        warehouse = SimpleNamespace(pk=10)
        query = self.s.Almacen.objects.select_related.return_value.filter
        query.return_value.first.return_value = warehouse
        order, movements = self.sale(almacen_id=10)
        query.assert_called_once_with(pk=10, activo=True, sucursal__activo=True,
                                      sucursal__negocio__tienda=self.tienda)
        calls = self.s.registrar_movimiento.call_args_list
        self.assertEqual([call.args[2] for call in calls], [-2, -3])
        self.assertTrue(all(call.kwargs['almacen'] is warehouse for call in calls))
        self.assertTrue(all(call.kwargs['order'] is order for call in calls))
        self.assertEqual(len(movements), 2)

    def test_almacen_omitido_conserva_fallback_del_servicio(self):
        self.sale()
        self.assertTrue(all(call.kwargs['almacen'] is None for call in self.s.registrar_movimiento.call_args_list))

    def test_rechaza_producto_ajeno_antes_de_crear_orden(self):
        self.query.order_by.return_value = [self.p1]
        with self.assertRaisesRegex(ValidationError, 'no pertenecen'):
            self.sale()
        self.s.StoreOrder.objects.create.assert_not_called()

    def test_rechaza_monedas_mezcladas_antes_de_crear_orden(self):
        self.p2.moneda = 'VES'
        with self.assertRaisesRegex(ValidationError, 'mezclar'):
            self.sale()
        self.s.StoreOrder.objects.create.assert_not_called()

    def test_almacen_inaccesible_no_crea_orden(self):
        self.s.Almacen.objects.select_related.return_value.filter.return_value.first.return_value = None
        with self.assertRaisesRegex(ValidationError, 'no está disponible'):
            self.sale(almacen_id=99)
        self.s.StoreOrder.objects.create.assert_not_called()

    def test_sin_tasa_y_notas_conserva_contrato(self):
        self.s.TasaCambio.vigente.return_value = None
        self.sale()
        data = self.s.StoreOrder.objects.create.call_args.kwargs
        self.assertIsNone(data['tasa_aplicada'])
        self.assertIsNone(data['notas'])

    def test_lineas_repetidas_no_pierden_cantidades(self):
        self.query.order_by.return_value = [self.p1]
        self.sale(items=[{'producto_id': 1, 'cantidad': 2}, {'producto_id': 1, 'cantidad': 3}])
        self.assertEqual(self.s.StoreOrder.objects.create.call_args.kwargs['total'], Decimal('12.50'))
        self.assertEqual([call.args[2] for call in self.s.registrar_movimiento.call_args_list], [-2, -3])

    def test_error_de_stock_sale_de_la_transaccion(self):
        self.s.registrar_movimiento.side_effect = ValidationError('Stock insuficiente')
        with self.assertRaisesRegex(ValidationError, 'Stock insuficiente'):
            self.sale()
        context = self.s.transaction.atomic.return_value
        self.assertIs(context.__exit__.call_args.args[0], ValidationError)
        # El doble sólo acredita propagación; el rollback real requiere PostgreSQL.

    def test_ticket_vacio_y_cantidades_invalidas_no_crean_orden(self):
        for items in ([], [{'producto_id': 1, 'cantidad': 0}], [{'producto_id': 1, 'cantidad': -1}]):
            with self.subTest(items=items), self.assertRaises(ValidationError):
                self.sale(items=items)
        self.s.StoreOrder.objects.create.assert_not_called()


if __name__ == '__main__':
    unittest.main()
