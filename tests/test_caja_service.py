"""Reglas de caja con dobles de ORM; no sustituye pruebas de concurrencia SQL."""
from datetime import datetime, timezone
from decimal import Decimal
import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch


class ValidationError(Exception):
    pass


class CajaServiceTests(unittest.TestCase):
    def setUp(self):
        modules = {name: ModuleType(name) for name in ('django', 'django.core', 'django.core.exceptions',
            'django.db', 'django.db.models', 'django.utils', 'store.models', 'store.services.ventas')}
        modules['django.core.exceptions'].ValidationError = ValidationError
        modules['django.db'].connection = MagicMock()
        modules['django.db'].transaction = MagicMock()
        modules['django.db.models'].Sum = MagicMock()
        modules['django.utils'].timezone = MagicMock()
        for name in ('Almacen', 'SesionCaja', 'MovimientoCaja', 'OperacionCaja'):
            setattr(modules['store.models'], name, MagicMock())
        modules['store.models'].SesionCaja.DoesNotExist = type('DoesNotExist', (Exception,), {})
        modules['store.services.ventas'].registrar_venta_presencial = MagicMock()
        path = Path(__file__).resolve().parents[1] / 'store/services/caja.py'
        spec = importlib.util.spec_from_file_location('caja_bajo_prueba', path)
        self.s = importlib.util.module_from_spec(spec)
        with patch.dict('sys.modules', modules):
            spec.loader.exec_module(self.s)
        self.groups = []
        self.session = SimpleNamespace(pk=1, almacen_id=2, almacen_nombre='Principal', sucursal_nombre='Sucursal',
            abierta=True, fondo_usd=Decimal('20.00'), fondo_ves=Decimal('100.00'), contado_usd=None, contado_ves=None,
            esperado_usd=None, esperado_ves=None, abierto_por=3, cerrado_por=None, notas_cierre='',
            abierto=datetime(2026, 9, 9, tzinfo=timezone.utc), cerrado=None, movimientos=MagicMock(), save=MagicMock())
        self.session.movimientos.values.return_value.annotate.side_effect = lambda **kwargs: self.groups
        self.s.SesionCaja.objects.select_for_update.return_value.get.return_value = self.session
        self.s.timezone.now.return_value = self.session.abierto
        self.store, self.user = SimpleNamespace(pk=1), SimpleNamespace(pk=3)

    def test_separa_moneda_y_excluye_pagos_no_efectivos(self):
        groups = [dict(moneda='USD', tipo='venta', medio_pago='efectivo', total='2.50'),
                  dict(moneda='USD', tipo='venta', medio_pago='zelle', total='50.00'),
                  dict(moneda='VES', tipo='venta', medio_pago='pago_movil', total='200.00'),
                  dict(moneda='VES', tipo='entrada', medio_pago='efectivo', total='10.00')]
        cash, sales = self.s.calcular_saldos('20', '100', groups)
        self.assertEqual(cash, {'USD': Decimal('22.50'), 'VES': Decimal('110.00')})
        self.assertEqual(sales['USD']['zelle'], Decimal('50'))

    def test_decimales_exactos_y_retiros(self):
        groups = [dict(moneda='USD', tipo='entrada', medio_pago='efectivo', total='0.10'),
                  dict(moneda='USD', tipo='retiro', medio_pago='efectivo', total='0.20')]
        cash, _ = self.s.calcular_saldos('0.30', '0', groups)
        self.assertEqual(cash['USD'], Decimal('0.20'))

    def test_retiro_superior_al_saldo_no_crea_movimiento(self):
        with self.assertRaisesRegex(ValidationError, 'supera'):
            self.s.ejecutar_operacion_caja(self.store, self.user, dict(accion='retiro', sesion_id=1, moneda='USD', monto=Decimal('20.01'), motivo='Retiro'))
        self.s.MovimientoCaja.objects.create.assert_not_called()

    def test_retiro_guarda_actor_moneda_y_motivo(self):
        self.s.ejecutar_operacion_caja(self.store, self.user, dict(accion='retiro', sesion_id=1, moneda='USD', monto=Decimal('20'), motivo='Depósito'))
        data = self.s.MovimientoCaja.objects.create.call_args.kwargs
        self.assertEqual((data['tipo'], data['usuario_id'], data['motivo'], data['moneda']), ('retiro', 3, 'Depósito', 'USD'))

    def test_cierre_guarda_conteos_esperados_y_diferencias(self):
        result = self.s.ejecutar_operacion_caja(self.store, self.user, dict(accion='cerrar', sesion_id=1, contado_usd=Decimal('19'), contado_ves=Decimal('103'), motivo='Conteo'))
        self.assertFalse(self.session.abierta)
        self.assertEqual(self.session.esperado_usd, Decimal('20'))
        self.assertEqual(result['sesion']['diferencia'], {'USD': '-1.00', 'VES': '3.00'})
        self.assertEqual(self.session.cerrado_por, 3)

    def test_sesion_cerrada_rechaza_venta_antes_de_tocar_stock(self):
        self.session.abierta = False
        with self.assertRaisesRegex(ValidationError, 'cerrada'):
            self.s.registrar_venta_en_caja(self.store, self.user, {'sesion_caja_id': 1})
        self.s.registrar_venta_presencial.assert_not_called()

    def test_otra_tienda_no_encuentra_sesion(self):
        query = self.s.SesionCaja.objects.select_for_update.return_value.get
        query.side_effect = self.s.SesionCaja.DoesNotExist
        with self.assertRaisesRegex(ValidationError, 'tu tienda'):
            self.s.bloquear_sesion(9, 1)
        query.assert_called_with(pk=1, tienda_id=9)

    def test_venta_en_otro_almacen_no_se_registra(self):
        with self.assertRaisesRegex(ValidationError, 'coincidir'):
            self.s.registrar_venta_en_caja(self.store, self.user, {'sesion_caja_id': 1, 'almacen_id': 9})
        self.s.registrar_venta_presencial.assert_not_called()

    def test_venta_registra_total_del_servidor_y_medio(self):
        order = SimpleNamespace(pk=42, total=Decimal('2.50'), moneda='USD')
        self.s.registrar_venta_presencial.return_value = (order, [])
        self.s.registrar_venta_en_caja(self.store, self.user, {'sesion_caja_id': 1, 'almacen_id': 2,
            'items': [{'producto_id': 1, 'cantidad': 1}], 'medio_pago': 'tarjeta'})
        data = self.s.MovimientoCaja.objects.create.call_args.kwargs
        self.assertEqual((data['order_id'], data['monto'], data['medio_pago']), (42, Decimal('2.50'), 'tarjeta'))

    def test_no_abre_segunda_caja_en_almacen(self):
        self.s.SesionCaja.objects.filter.return_value.exists.return_value = True
        with self.assertRaisesRegex(ValidationError, 'ya tiene'):
            self.s.ejecutar_operacion_caja(self.store, self.user, {'accion': 'abrir', 'almacen_id': 2})
        self.s.SesionCaja.objects.create.assert_not_called()

    def test_almacen_inactivo_o_ajeno_no_abre_caja(self):
        self.s.Almacen.objects.select_for_update.return_value.select_related.return_value.filter.return_value.first.return_value = None
        with self.assertRaisesRegex(ValidationError, 'activo de tu tienda'):
            self.s.ejecutar_operacion_caja(self.store, self.user, {'accion': 'abrir', 'almacen_id': 9})

    def test_sin_migracion_no_consulta_datos_de_caja(self):
        self.s.connection.introspection.table_names.return_value = []
        self.assertFalse(self.s.caja_disponible())
        self.s.SesionCaja.objects.filter.assert_not_called()
