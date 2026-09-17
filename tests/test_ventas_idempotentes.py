"""Contrato del servicio con dobles de ORM. Concurrencia SQL se prueba en la suite QA."""
import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch


class VentasIdempotentesTests(unittest.TestCase):
    def setUp(self):
        modules = {name: ModuleType(name) for name in ('django', 'django.db', 'store.models')}
        modules['django.db'].connection = MagicMock()
        modules['django.db'].transaction = MagicMock()
        modules['store.models'].OperacionVentaPresencial = MagicMock()
        path = Path(__file__).resolve().parents[1] / 'store/services/ventas_idempotentes.py'
        spec = importlib.util.spec_from_file_location('idempotencia_bajo_prueba', path)
        self.s = importlib.util.module_from_spec(spec)
        with patch.dict('sys.modules', modules):
            spec.loader.exec_module(self.s)
        self.rows = {}
        manager = self.s.OperacionVentaPresencial.objects
        manager.get_or_create.side_effect = self.get_or_create
        manager.select_for_update.return_value.get.side_effect = lambda pk: next(row for row in self.rows.values() if row.pk == pk)
        self.create = MagicMock(return_value={'order': {'id': 15, 'total': '10.00'}, 'movimientos': [{'id': 20}]})

    def get_or_create(self, tienda_id, clave, defaults=None):
        key = (tienda_id, clave)
        created = key not in self.rows
        if created:
            self.rows[key] = SimpleNamespace(pk=len(self.rows)+1, cancelada=False, respuesta=None,
                                            huella=(defaults or {}).get('huella', ''), save=MagicMock())
        return self.rows[key], created

    def confirm(self, store=1, key='clave', fingerprint='huella'):
        return self.s.confirmar_operacion(store, key, fingerprint, self.create)

    def test_reintento_recupera_comprobante_sin_ejecutar_venta_otra_vez(self):
        first, repeated = self.confirm()
        self.assertFalse(repeated)
        self.create.return_value = {'order': {'id': 99, 'total': '20.00'}}
        second, repeated = self.confirm()
        self.assertTrue(repeated)
        self.assertEqual(first, second)
        self.create.assert_called_once()
        self.s.OperacionVentaPresencial.objects.select_for_update.assert_called()

    def test_clave_con_ticket_modificado_se_rechaza(self):
        self.confirm()
        with self.assertRaises(self.s.ConflictoOperacion):
            self.confirm(fingerprint='otra')
        self.create.assert_called_once()

    def test_misma_clave_en_otro_negocio_es_independiente(self):
        self.confirm()
        _, repeated = self.confirm(store=2)
        self.assertFalse(repeated)
        self.assertEqual(self.create.call_count, 2)

    def test_cancelar_antes_impide_cobro_retrasado(self):
        self.assertIsNone(self.s.cancelar_operacion(1, 'clave'))
        with self.assertRaises(self.s.ConflictoOperacion):
            self.confirm()
        self.create.assert_not_called()

    def test_cancelar_despues_devuelve_venta_confirmada(self):
        receipt, _ = self.confirm()
        self.assertEqual(self.s.cancelar_operacion(1, 'clave'), receipt)
        self.assertFalse(self.rows[(1, 'clave')].cancelada)

    def test_cancelacion_repetida_conserva_bloqueo(self):
        self.s.cancelar_operacion(1, 'clave')
        self.s.cancelar_operacion(1, 'clave')
        self.assertEqual(len(self.rows), 1)
        self.assertTrue(self.rows[(1, 'clave')].cancelada)

    def test_error_de_venta_sale_de_transaccion_sin_confirmar(self):
        self.create.side_effect = ValueError('Stock insuficiente')
        with self.assertRaises(ValueError):
            self.confirm()
        self.assertIsNone(self.rows[(1, 'clave')].respuesta)
        self.rows[(1, 'clave')].save.assert_not_called()
        self.assertIs(self.s.transaction.atomic.return_value.__exit__.call_args.args[0], ValueError)

    def test_error_al_guardar_comprobante_propaga_para_revertir_venta(self):
        row, _ = self.get_or_create(1, 'clave', {'huella': 'huella'})
        row.save.side_effect = ValueError('Error de escritura')
        with self.assertRaises(ValueError):
            self.confirm()
        self.assertIs(self.s.transaction.atomic.return_value.__exit__.call_args.args[0], ValueError)

    def test_huella_cubre_lineas_almacen_y_notas(self):
        items = [{'producto_id': 1, 'cantidad': 2}]
        original = self.s.huella_venta(items, 1, 'Venta')
        self.assertEqual(original, self.s.huella_venta([{'cantidad': 2, 'producto_id': 1}], 1, 'Venta'))
        for args in ((items, 2, 'Venta'), (items, 1, 'Otra'), ([{'producto_id': 1, 'cantidad': 3}], 1, 'Venta')):
            self.assertNotEqual(original, self.s.huella_venta(*args))

    def test_despliegue_sin_tabla_no_consulta_operaciones(self):
        self.s.connection.introspection.table_names.return_value = []
        self.assertFalse(self.s.idempotencia_disponible())
        self.s.OperacionVentaPresencial.objects.get_or_create.assert_not_called()

    def test_caja_utiliza_registro_de_operaciones_separado(self):
        model = MagicMock()
        model.objects.get_or_create.side_effect = self.get_or_create
        model.objects.select_for_update.return_value.get.side_effect = lambda pk: next(row for row in self.rows.values() if row.pk == pk)
        self.s.confirmar_operacion(1, 'clave', 'huella', self.create, modelo=model)
        self.s.OperacionVentaPresencial.objects.get_or_create.assert_not_called()
        self.assertEqual(self.s.cancelar_operacion(1, 'clave', modelo=model), self.create.return_value)

    def test_huella_legacy_se_conserva_y_caja_incluye_sesion_y_medio(self):
        import hashlib
        items = [{'producto_id': 1, 'cantidad': 2}]
        expected = hashlib.sha256(b'{"almacen_id":1,"items":[{"cantidad":2,"producto_id":1}],"notas":""}').hexdigest()
        self.assertEqual(self.s.huella_venta(items, 1), expected)
        fingerprint = self.s.huella_venta(items, 1, contexto={'sesion_id': 1, 'medio_pago': 'efectivo'})
        self.assertNotEqual(fingerprint, expected)
        self.assertNotEqual(fingerprint, self.s.huella_venta(items, 1, contexto={'sesion_id': 2, 'medio_pago': 'efectivo'}))
        self.assertNotEqual(fingerprint, self.s.huella_venta(items, 1, contexto={'sesion_id': 1, 'medio_pago': 'zelle'}))
