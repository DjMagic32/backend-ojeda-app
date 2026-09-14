"""Reglas de gastos con dobles de ORM; no sustituye pruebas SQL/concurrencia."""
from datetime import datetime, timezone
from decimal import Decimal
import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch


class ValidationError(Exception):
    pass


class GastosServiceTests(unittest.TestCase):
    def setUp(self):
        modules = {name: ModuleType(name) for name in (
            'django', 'django.core', 'django.core.exceptions', 'django.db', 'store.models',
        )}
        modules['django.core.exceptions'].ValidationError = ValidationError
        modules['django.db'].connection = MagicMock()
        modules['django.db'].transaction = MagicMock()
        for name in ('Gasto', 'OperacionGasto', 'Sucursal', 'TasaCambio'):
            setattr(modules['store.models'], name, MagicMock())
        modules['store.models'].Gasto.DoesNotExist = type('DoesNotExist', (Exception,), {})
        path = Path(__file__).resolve().parents[1] / 'store/services/gastos.py'
        spec = importlib.util.spec_from_file_location('gastos_bajo_prueba', path)
        self.s = importlib.util.module_from_spec(spec)
        with patch.dict('sys.modules', modules):
            spec.loader.exec_module(self.s)
        self.store, self.user = SimpleNamespace(pk=1), SimpleNamespace(pk=3)
        self.creado = datetime(2026, 9, 14, tzinfo=timezone.utc)
        self.s.TasaCambio.vigente.return_value = SimpleNamespace(valor_bs=Decimal('45.0000'))
        self.s.Sucursal.objects.filter.return_value.exists.return_value = True
        self.gasto = SimpleNamespace(
            pk=7, tienda_id=1, sucursal_id=None, tipo='variable', categoria='Insumos',
            descripcion='', monto=Decimal('50.00'), moneda='USD', tasa_aplicada=Decimal('45.0000'),
            anulado=False, notas='', creado=self.creado, save=MagicMock(),
        )
        self.s.Gasto.objects.create.return_value = self.gasto
        self.s.Gasto.objects.select_for_update.return_value.get.return_value = self.gasto

    def test_crear_gasto_captura_tasa_vigente(self):
        resultado = self.s.crear_gasto(self.store, self.user, {
            'tipo': 'variable', 'categoria': 'Insumos', 'monto': Decimal('50.00'), 'moneda': 'USD',
        })
        kwargs = self.s.Gasto.objects.create.call_args.kwargs
        self.assertEqual(kwargs['tasa_aplicada'], Decimal('45.0000'))
        self.assertEqual(kwargs['tienda_id'], 1)
        self.assertEqual(resultado['gasto']['categoria'], 'Insumos')

    def test_crear_gasto_sin_tasa_vigente_guarda_none(self):
        self.s.TasaCambio.vigente.return_value = None
        self.s.crear_gasto(self.store, self.user, {
            'tipo': 'fijo', 'categoria': 'Alquiler', 'monto': Decimal('200.00'), 'moneda': 'USD',
        })
        kwargs = self.s.Gasto.objects.create.call_args.kwargs
        self.assertIsNone(kwargs['tasa_aplicada'])

    def test_crear_gasto_con_sucursal_ajena_se_rechaza(self):
        self.s.Sucursal.objects.filter.return_value.exists.return_value = False
        with self.assertRaisesRegex(ValidationError, 'sucursal activa'):
            self.s.crear_gasto(self.store, self.user, {
                'tipo': 'fijo', 'categoria': 'Alquiler', 'monto': Decimal('10'), 'moneda': 'USD', 'sucursal_id': 99,
            })
        self.s.Gasto.objects.create.assert_not_called()

    def test_crear_gasto_con_sucursal_propia_se_permite(self):
        self.s.crear_gasto(self.store, self.user, {
            'tipo': 'fijo', 'categoria': 'Alquiler', 'monto': Decimal('10'), 'moneda': 'USD', 'sucursal_id': 2,
        })
        kwargs = self.s.Gasto.objects.create.call_args.kwargs
        self.assertEqual(kwargs['sucursal_id'], 2)

    def test_anular_gasto_agrega_motivo_a_notas(self):
        resultado = self.s.anular_gasto(self.store, self.user, 7, motivo='Registrado por error')
        self.assertTrue(self.gasto.anulado)
        self.assertIn('Registrado por error', self.gasto.notas)
        self.assertEqual(resultado['gasto']['anulado'], True)

    def test_anular_gasto_ya_anulado_se_rechaza(self):
        self.gasto.anulado = True
        with self.assertRaisesRegex(ValidationError, 'ya está anulado'):
            self.s.anular_gasto(self.store, self.user, 7)

    def test_gasto_inexistente_o_de_otra_tienda_falla(self):
        self.s.Gasto.objects.select_for_update.return_value.get.side_effect = self.s.Gasto.DoesNotExist
        with self.assertRaisesRegex(ValidationError, 'no está disponible'):
            self.s.anular_gasto(self.store, self.user, 999)


if __name__ == '__main__':
    unittest.main()
