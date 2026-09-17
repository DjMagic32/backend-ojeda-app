"""Regresiones del servicio real con dobles de ORM, sin arrancar Django.

Ejecutar: python3 -m unittest discover -s tests -v
No comprueban SQL, rollback ni concurrencia de PostgreSQL.
"""
import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch


class ValidationError(Exception):
    pass


def cargar_servicio():
    modules = {
        name: ModuleType(name)
        for name in ('django', 'django.core', 'django.core.exceptions',
                     'django.db', 'django.db.models', 'store.models')
    }
    modules['django.core.exceptions'].ValidationError = ValidationError
    modules['django.db'].transaction = MagicMock()
    modules['django.db.models'].Sum = MagicMock()
    for name in ('Almacen', 'InventarioAlmacen', 'MovimientoStock',
                 'ProductoTienda', 'TransferenciaInventario'):
        setattr(modules['store.models'], name, MagicMock())
    path = Path(__file__).resolve().parents[1] / 'store/services/inventario.py'
    spec = importlib.util.spec_from_file_location('inventario_bajo_prueba', path)
    service = importlib.util.module_from_spec(spec)
    with patch.dict('sys.modules', modules):
        spec.loader.exec_module(service)
    service.ProductoTienda.TIPO_SERVICIO = 'SERVICIO'
    for key, value in {'TIPO_ENTRADA': 'entrada', 'TIPO_AJUSTE': 'ajuste',
                       'TIPO_VENTA': 'venta', 'TIPO_TRANSFERENCIA': 'transferencia',
                       'ORIGEN_AJUSTE_MANUAL': 'ajuste_manual',
                       'ORIGEN_TRANSFERENCIA': 'transferencia'}.items():
        setattr(service.MovimientoStock, key, value)
    return service


class InventarioServiceTests(unittest.TestCase):
    def setUp(self):
        self.s = cargar_servicio()
        self.product = SimpleNamespace(pk=1, tienda_id=1, nombre='Arroz',
                                       stock=30, tipo='PRODUCTO', save=MagicMock())
        branch = SimpleNamespace(activo=True, negocio_id=1,
                                 negocio=SimpleNamespace(tienda_id=1))
        self.origin = SimpleNamespace(pk=1, activo=True, nombre='Principal', sucursal=branch)
        self.destination = SimpleNamespace(pk=2, activo=True, nombre='Secundario', sucursal=branch)
        self.balances = []
        self.add_balance(self.origin, 10)
        self.add_balance(self.destination, 20)
        self.s.ProductoTienda.objects.select_for_update.return_value.get.return_value = self.product
        self.s.Almacen.objects.filter.return_value.order_by.return_value.first.return_value = self.origin
        self.s.Almacen.objects.select_for_update.return_value.select_related.return_value.filter.return_value.order_by.return_value = [self.origin, self.destination]
        manager = self.s.InventarioAlmacen.objects
        manager.filter.side_effect = self.query_balances
        manager.select_for_update.return_value.filter.side_effect = self.query_balances
        manager.select_for_update.return_value.get.side_effect = lambda pk: next(b for b in self.balances if b.pk == pk)
        manager.get_or_create.side_effect = self.get_or_create_balance
        manager.create.side_effect = lambda producto, almacen, cantidad: self.add_balance(almacen, cantidad)
        self.s.MovimientoStock.objects.create.side_effect = lambda **kwargs: SimpleNamespace(**kwargs)

    def add_balance(self, warehouse, quantity):
        row = SimpleNamespace(pk=len(self.balances) + 1, almacen_id=warehouse.pk,
                              cantidad=quantity, save=MagicMock())
        self.balances.append(row)
        return row

    def query_balances(self, **filters):
        rows = self.balances
        if 'almacen_id__in' in filters:
            rows = [row for row in rows if row.almacen_id in filters['almacen_id__in']]
        query = MagicMock()
        query.exists.return_value = bool(rows)
        query.order_by.return_value = rows
        query.aggregate.return_value = {'total': sum(row.cantidad for row in rows)}
        return query

    def get_or_create_balance(self, producto, almacen, defaults):
        existing = next((b for b in self.balances if b.almacen_id == almacen.pk), None)
        if existing:
            return existing, False
        return self.add_balance(almacen, defaults['cantidad']), True

    def adjust(self, **kwargs):
        return self.s.registrar_movimiento(
            self.product, 'ajuste', kwargs.pop('delta', 0), 'ajuste_manual', **kwargs)

    def test_conteo_absoluto_usa_almacen_y_conserva_los_demas(self):
        movement = self.adjust(almacen=self.origin, nuevo_stock=11)
        self.assertEqual([b.cantidad for b in self.balances], [11, 20])
        self.assertEqual((movement.cantidad, movement.stock_resultante), (1, 31))

    def test_cliente_sin_almacen_cuenta_solo_el_principal(self):
        movement = self.adjust(nuevo_stock=11)
        self.assertEqual((movement.stock_almacen_resultante, self.product.stock), (11, 31))

    def test_delta_positivo_y_negativo_conservan_otro_almacen(self):
        self.adjust(almacen=self.origin, delta=1)
        self.adjust(almacen=self.origin, delta=-1)
        self.assertEqual([b.cantidad for b in self.balances], [10, 20])
        self.assertEqual(self.product.stock, 30)

    def test_conteo_repetido_no_crea_movimiento(self):
        self.assertIsNone(self.adjust(almacen=self.origin, nuevo_stock=10))
        self.s.MovimientoStock.objects.create.assert_not_called()

    def test_usa_producto_recargado_bajo_bloqueo(self):
        # El objeto recibido tiene 30, pero el registro recargado ya tiene 35.
        locked = SimpleNamespace(**vars(self.product))
        locked.stock = 35
        self.balances[0].cantidad = 15
        self.s.ProductoTienda.objects.select_for_update.return_value.get.return_value = locked
        movement = self.adjust(almacen=self.origin, nuevo_stock=16)
        self.assertEqual((movement.cantidad, movement.stock_resultante), (1, 36))
        self.s.ProductoTienda.objects.select_for_update.assert_called_once()

    def test_activar_control_en_cero_registra_movimiento(self):
        self.product.stock = None
        self.balances.clear()
        movement = self.adjust(almacen=self.origin, nuevo_stock=0)
        self.assertEqual((self.product.stock, movement.stock_almacen_resultante), (0, 0))

    def test_producto_legado_sin_detalle_no_suma_dos_veces_el_total(self):
        self.balances.clear()
        movement = self.adjust(almacen=self.origin, nuevo_stock=31)
        self.assertEqual((movement.cantidad, self.product.stock), (1, 31))

    def test_venta_sin_stock_suficiente_no_escribe_saldos(self):
        with self.assertRaisesRegex(ValidationError, 'Stock insuficiente'):
            self.s.registrar_movimiento(self.product, 'venta', -11, 'venta_presencial', almacen=self.origin)
        self.product.save.assert_not_called()
        self.balances[0].save.assert_not_called()
        self.s.MovimientoStock.objects.create.assert_not_called()

    def test_no_ajusta_servicios(self):
        self.product.tipo = 'SERVICIO'
        with self.assertRaisesRegex(ValidationError, 'servicios'):
            self.adjust(nuevo_stock=0)

    def test_delta_no_activa_control_de_stock(self):
        self.product.stock = None
        with self.assertRaisesRegex(ValidationError, 'no tiene control'):
            self.adjust(delta=1)

    def test_venta_servicio_no_modifica_inventario(self):
        self.product.tipo = 'SERVICIO'
        movement = self.s.registrar_movimiento(self.product, 'venta', -1, 'venta_presencial')
        self.assertIsNone(movement.stock_resultante)
        self.product.save.assert_not_called()

    def test_rechaza_almacen_de_otra_tienda(self):
        self.origin.sucursal.negocio.tienda_id = 2
        with self.assertRaisesRegex(ValidationError, 'no pertenece'):
            self.adjust(almacen=self.origin, delta=1)

    def test_rechaza_almacen_inactivo(self):
        self.origin.activo = False
        with self.assertRaisesRegex(ValidationError, 'no está disponible'):
            self.adjust(almacen=self.origin, delta=1)

    def test_sin_principal_no_desincroniza_inventario_existente(self):
        self.s.Almacen.objects.filter.return_value.order_by.return_value.first.return_value = None
        with self.assertRaisesRegex(ValidationError, 'Selecciona un almacén'):
            self.adjust(delta=1)
        self.product.save.assert_not_called()

    def test_tienda_legada_sin_almacen_conserva_ajustes(self):
        self.s.Almacen.objects.filter.return_value.order_by.return_value.first.return_value = None
        self.balances.clear()
        movement = self.adjust(nuevo_stock=31)
        self.assertEqual((movement.cantidad, self.product.stock), (1, 31))

    def test_transferencia_no_copia_existencias_de_un_tercer_almacen(self):
        self.balances.clear()
        third = SimpleNamespace(pk=3)
        self.add_balance(third, 30)
        with self.assertRaisesRegex(ValidationError, 'Stock insuficiente'):
            self.s.transferir_stock(self.product, self.origin, self.destination, 1, usuario=None)
        self.assertEqual(sum(b.cantidad for b in self.balances), 30)
        self.s.TransferenciaInventario.objects.create.assert_not_called()
        self.s.MovimientoStock.objects.create.assert_not_called()

    def test_transferencia_conserva_total_y_dos_movimientos(self):
        self.s.transferir_stock(self.product, self.origin, self.destination, 3, usuario=None)
        self.assertEqual([b.cantidad for b in self.balances], [7, 23])
        self.assertEqual(self.product.stock, 30)
        movements = self.s.MovimientoStock.objects.create.call_args_list
        self.assertEqual([call.kwargs['cantidad'] for call in movements], [-3, 3])


if __name__ == '__main__':
    unittest.main()
