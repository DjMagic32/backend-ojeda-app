"""Reglas de cuentas por pagar con dobles de ORM; no sustituye pruebas SQL/concurrencia."""
from datetime import datetime, timezone
from decimal import Decimal
import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch


class ValidationError(Exception):
    pass


class PagosServiceTests(unittest.TestCase):
    def setUp(self):
        modules = {name: ModuleType(name) for name in (
            'django', 'django.core', 'django.core.exceptions', 'django.db', 'store.models',
        )}
        modules['django.core.exceptions'].ValidationError = ValidationError
        modules['django.db'].connection = MagicMock()
        modules['django.db'].transaction = MagicMock()
        for name in ('CuentaPorPagar', 'AbonoCuentaPorPagar', 'OperacionCuentaPorPagar', 'TasaCambio'):
            setattr(modules['store.models'], name, MagicMock())
        modules['store.models'].CuentaPorPagar.DoesNotExist = type('DoesNotExist', (Exception,), {})
        modules['store.models'].CuentaPorPagar.ESTADO_PENDIENTE = 'pendiente'
        modules['store.models'].CuentaPorPagar.ESTADO_PARCIAL = 'parcial'
        modules['store.models'].CuentaPorPagar.ESTADO_PAGADA = 'pagada'
        modules['store.models'].CuentaPorPagar.ESTADO_ANULADA = 'anulada'
        path = Path(__file__).resolve().parents[1] / 'store/services/pagos.py'
        spec = importlib.util.spec_from_file_location('pagos_bajo_prueba', path)
        self.s = importlib.util.module_from_spec(spec)
        with patch.dict('sys.modules', modules):
            spec.loader.exec_module(self.s)
        self.store, self.user = SimpleNamespace(pk=1), SimpleNamespace(pk=3)
        self.creado = datetime(2026, 9, 14, tzinfo=timezone.utc)
        self.cuenta = SimpleNamespace(
            pk=5, tienda_id=1, proveedor_nombre='Distribuidora ABC', proveedor_telefono='',
            monto_usd=Decimal('100.00'), saldo_usd=Decimal('100.00'), tasa_emision=Decimal('40.0000'),
            estado='pendiente', vencimiento=None, notas='', creado=self.creado, save=MagicMock(),
        )
        self.s.CuentaPorPagar.objects.select_for_update.return_value.get.return_value = self.cuenta
        self.s.TasaCambio.vigente.return_value = SimpleNamespace(valor_bs=Decimal('45.0000'))
        self.s.AbonoCuentaPorPagar.objects.create.side_effect = \
            lambda **kwargs: SimpleNamespace(pk=9, cuenta_id=5, creado=self.creado, **kwargs)

    def test_crear_cuenta_usa_tasa_vigente_como_saldo_inicial(self):
        self.s.TasaCambio.vigente.return_value = SimpleNamespace(valor_bs=Decimal('40.0000'))
        self.s.CuentaPorPagar.objects.create.return_value = self.cuenta
        resultado = self.s.crear_cuenta_por_pagar(
            self.store, self.user, {'proveedor_nombre': 'Distribuidora ABC', 'monto_usd': Decimal('100.00')},
        )
        kwargs = self.s.CuentaPorPagar.objects.create.call_args.kwargs
        self.assertEqual((kwargs['monto_usd'], kwargs['saldo_usd'], kwargs['tasa_emision']),
                          (Decimal('100.00'), Decimal('100.00'), Decimal('40.0000')))
        self.assertEqual(resultado['cuenta']['saldo_usd'], '100.00')

    def test_crear_cuenta_sin_tasa_vigente_falla(self):
        self.s.TasaCambio.vigente.return_value = None
        with self.assertRaisesRegex(ValidationError, 'tasa de cambio'):
            self.s.crear_cuenta_por_pagar(self.store, self.user, {'proveedor_nombre': 'X', 'monto_usd': Decimal('10')})
        self.s.CuentaPorPagar.objects.create.assert_not_called()

    def test_abono_con_tasa_al_alza_registra_perdida_cambiaria(self):
        # Tasa subió de 40 a 45: pagar la misma deuda en USD cuesta más bolívares -> pérdida.
        resultado = self.s.registrar_abono(self.store, self.user, {'cuenta_id': 5, 'monto_usd': Decimal('40.00')})
        kwargs = self.s.AbonoCuentaPorPagar.objects.create.call_args.kwargs
        self.assertEqual(kwargs['diferencial_cambiario_ves'], Decimal('-200.00'))
        self.assertEqual(kwargs['monto_ves_equivalente'], Decimal('1800.00'))
        self.assertEqual(self.cuenta.saldo_usd, Decimal('60.00'))
        self.assertEqual(self.cuenta.estado, 'parcial')
        self.assertEqual(resultado['abono']['diferencial_cambiario_ves'], '-200.00')

    def test_abono_con_tasa_a_la_baja_registra_ganancia_cambiaria(self):
        self.s.TasaCambio.vigente.return_value = SimpleNamespace(valor_bs=Decimal('35.0000'))
        self.s.registrar_abono(self.store, self.user, {'cuenta_id': 5, 'monto_usd': Decimal('40.00')})
        kwargs = self.s.AbonoCuentaPorPagar.objects.create.call_args.kwargs
        self.assertEqual(kwargs['diferencial_cambiario_ves'], Decimal('200.00'))

    def test_abono_total_marca_cuenta_pagada(self):
        self.s.registrar_abono(self.store, self.user, {'cuenta_id': 5, 'monto_usd': Decimal('100.00')})
        self.assertEqual(self.cuenta.saldo_usd, Decimal('0.00'))
        self.assertEqual(self.cuenta.estado, 'pagada')

    def test_abono_mayor_al_saldo_se_rechaza(self):
        with self.assertRaisesRegex(ValidationError, 'supera'):
            self.s.registrar_abono(self.store, self.user, {'cuenta_id': 5, 'monto_usd': Decimal('100.01')})
        self.s.AbonoCuentaPorPagar.objects.create.assert_not_called()

    def test_abono_sobre_cuenta_pagada_se_rechaza(self):
        self.cuenta.estado = 'pagada'
        with self.assertRaisesRegex(ValidationError, 'no admite abonos'):
            self.s.registrar_abono(self.store, self.user, {'cuenta_id': 5, 'monto_usd': Decimal('1')})

    def test_abono_sin_tasa_vigente_falla(self):
        self.s.TasaCambio.vigente.return_value = None
        with self.assertRaisesRegex(ValidationError, 'tasa de cambio'):
            self.s.registrar_abono(self.store, self.user, {'cuenta_id': 5, 'monto_usd': Decimal('10')})
        self.s.AbonoCuentaPorPagar.objects.create.assert_not_called()

    def test_cuenta_inexistente_o_de_otra_tienda_falla(self):
        self.s.CuentaPorPagar.objects.select_for_update.return_value.get.side_effect = \
            self.s.CuentaPorPagar.DoesNotExist
        with self.assertRaisesRegex(ValidationError, 'no está disponible'):
            self.s.registrar_abono(self.store, self.user, {'cuenta_id': 999, 'monto_usd': Decimal('1')})

    def test_anular_cuenta_sin_abonos_se_permite(self):
        resultado = self.s.anular_cuenta(self.store, self.user, 5, motivo='Devolución de mercancía')
        self.assertEqual(self.cuenta.estado, 'anulada')
        self.assertIn('Devolución de mercancía', self.cuenta.notas)
        self.assertEqual(resultado['cuenta']['estado'], 'anulada')

    def test_anular_cuenta_con_abonos_se_rechaza(self):
        self.cuenta.saldo_usd = Decimal('60.00')
        with self.assertRaisesRegex(ValidationError, 'sin abonos registrados'):
            self.s.anular_cuenta(self.store, self.user, 5)

    def test_anular_cuenta_ya_pagada_se_rechaza(self):
        self.cuenta.estado = 'pagada'
        with self.assertRaisesRegex(ValidationError, 'ya no se puede anular'):
            self.s.anular_cuenta(self.store, self.user, 5)


if __name__ == '__main__':
    unittest.main()
