"""REST/JWT y concurrencia reales; ejecutar sólo con integration_settings y PostgreSQL QA.

No forma parte de los tests locales con dobles de ORM de tests/.
"""
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
import json
from threading import Barrier
import unittest
from uuid import uuid4

from django.conf import settings
from django.core.management import call_command
from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from store.models import (
    Almacen, InventarioAlmacen, MovimientoStock, NegocioMiembro, ProductoTienda,
    StoreOrder, StoreOrderItem, Tienda, TransferenciaInventario, Usuario,
    OperacionVentaPresencial,
)
from store.services.inventario import transferir_stock


@unittest.skipUnless(
    settings.SETTINGS_MODULE == 'backend_ojeda.integration_settings',
    'Requiere integration_settings y PostgreSQL QA dedicado.',
)
class InventarioPostgresTests(TransactionTestCase):
    def setUp(self):
        super().setUp()
        if connection.vendor != 'postgresql' or not connection.settings_dict['NAME'].startswith('test_tuplaza_qa_'):
            self.fail('La suite sólo puede operar sobre la base creada por el runner de QA.')
        self.owner_a = self.user('a', Usuario.ES_TIENDA)
        self.owner_b = self.user('b', Usuario.ES_TIENDA)
        self.customer = self.user('cliente', Usuario.ES_CLIENTE)
        self.store_a = Tienda.objects.create(usuario=self.owner_a, nombre='QA negocio A')
        self.store_b = Tienda.objects.create(usuario=self.owner_b, nombre='QA negocio B')
        self.a1 = Almacen.objects.get(sucursal__negocio__tienda=self.store_a, codigo='PRINCIPAL')
        self.a2 = Almacen.objects.create(sucursal=self.a1.sucursal, codigo='QA2', nombre='QA secundario')
        self.b1 = Almacen.objects.get(sucursal__negocio__tienda=self.store_b, codigo='PRINCIPAL')
        self.product = self.producto('QA producto', 10)
        self.token_a = str(RefreshToken.for_user(self.owner_a).access_token)
        self.client_a = self.client_for(self.token_a)
        self.client_b = self.client_for(str(RefreshToken.for_user(self.owner_b).access_token))
        self.client_customer = self.client_for(str(RefreshToken.for_user(self.customer).access_token))

    def user(self, name, role):
        return Usuario.objects.create_user(username=f'{name}@qa.invalid', email=f'{name}@qa.invalid',
                                           password='SoloPruebas123!', rol=role)

    def producto(self, name, stock, **kwargs):
        return ProductoTienda.objects.create(tienda=self.store_a, nombre=name,
                                             descripcion='Fixture QA', precio='2.50', stock=stock, **kwargs)

    @staticmethod
    def client_for(token):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        return client

    def balance(self, warehouse):
        return InventarioAlmacen.objects.get(producto=self.product, almacen=warehouse).cantidad

    def counts(self):
        return tuple(model.objects.count() for model in (
            StoreOrder, StoreOrderItem, MovimientoStock, TransferenciaInventario, InventarioAlmacen,
        ))

    def sale_payload(self, quantity=1, warehouse=None):
        return {'items': [{'producto_id': self.product.pk, 'cantidad': quantity}],
                'almacen_id': (warehouse or self.a1).pk}

    def adjustment_url(self):
        return f'/api/store/productos-tienda/{self.product.pk}/ajustar-stock/'

    def test_venta_usa_almacen_y_conserva_otro_saldo(self):
        transferir_stock(self.product, self.a1, self.a2, 4, self.owner_a)
        response = self.client_a.post('/api/store/ventas-presenciales/', self.sale_payload(3, self.a2), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual((self.balance(self.a1), self.balance(self.a2)), (6, 1))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 7)
        self.assertEqual(response.data['order']['estado'], 'completed')
        order = StoreOrder.objects.get(pk=response.data['order']['id'])
        self.assertEqual(order.canal, 'presencial')
        self.assertEqual(str(order.total), '7.50')
        self.assertEqual(response.data['movimientos'][0]['almacen'], self.a2.pk)

    def test_insuficiencia_en_segunda_linea_revierte_toda_la_venta(self):
        empty = self.producto('QA sin unidades', 0)
        before = self.counts()
        payload = self.sale_payload()
        payload['items'].append({'producto_id': empty.pk, 'cantidad': 1})
        response = self.client_a.post('/api/store/ventas-presenciales/', payload, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.balance(self.a1), 10)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)

    def test_lineas_repetidas_no_sobrevenden(self):
        before = self.counts()
        payload = self.sale_payload(6)
        payload['items'].append({'producto_id': self.product.pk, 'cantidad': 6})
        response = self.client_a.post('/api/store/ventas-presenciales/', payload, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.balance(self.a1), 10)

    def test_aislamiento_rest_entre_dos_negocios(self):
        own = InventarioAlmacen.objects.get(producto=self.product, almacen=self.a1)
        response = self.client_b.get('/api/store/inventario-almacenes/', {'producto': self.product.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])
        self.assertEqual(self.client_b.get(f'/api/store/inventario-almacenes/{own.pk}/').status_code, 404)
        before = self.counts()
        for client, path, payload in (
            (self.client_b, '/api/store/ventas-presenciales/', self.sale_payload()),
            (self.client_b, self.adjustment_url(), {'delta': 1, 'almacen_id': self.a1.pk}),
            (self.client_a, '/api/store/ventas-presenciales/', self.sale_payload(1, self.b1)),
            (self.client_a, '/api/store/transferencias-inventario/', {
                'producto_id': self.product.pk, 'almacen_origen_id': self.a1.pk,
                'almacen_destino_id': self.b1.pk, 'cantidad': 1}),
        ):
            with self.subTest(path=path):
                response = client.post(path, payload, format='json')
                self.assertIn(response.status_code, (400, 403, 404), response.data)
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.balance(self.a1), 10)

    def test_cliente_y_anonimo_no_operan_stock(self):
        for client in (APIClient(), self.client_customer):
            for path, payload in (
                ('/api/store/ventas-presenciales/', self.sale_payload()),
                (self.adjustment_url(), {'delta': 1}),
            ):
                with self.subTest(path=path, client=client):
                    self.assertIn(client.post(path, payload, format='json').status_code, (401, 403))
        self.assertEqual(self.balance(self.a1), 10)

    def test_miembro_desactivado_pierde_lectura(self):
        member = NegocioMiembro.objects.create(negocio=self.store_a.negocio, usuario=self.customer, rol='admin')
        self.assertTrue(self.client_customer.get('/api/store/inventario-almacenes/').data)
        member.activo = False
        member.save(update_fields=['activo'])
        response = self.client_customer.get('/api/store/inventario-almacenes/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_almacen_inactivo_no_permite_venta(self):
        self.a1.activo = False
        self.a1.save(update_fields=['activo'])
        before = self.counts()
        response = self.client_a.post('/api/store/ventas-presenciales/', self.sale_payload(), format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(self.counts(), before)

    def test_servicios_sin_control_y_monedas(self):
        service = self.producto('QA servicio', 0, tipo=ProductoTienda.TIPO_SERVICIO)
        uncontrolled = self.producto('QA sin control', None)
        for product in (service, uncontrolled):
            response = self.client_a.post('/api/store/ventas-presenciales/', {
                'items': [{'producto_id': product.pk, 'cantidad': 20}], 'almacen_id': self.a2.pk,
            }, format='json')
            self.assertEqual(response.status_code, 201, response.data)
            self.assertIsNone(response.data['movimientos'][0]['stock_resultante'])
            self.assertFalse(InventarioAlmacen.objects.filter(producto=product).exists())
        ves = self.producto('QA bolívares', 10, moneda='VES')
        before = self.counts()
        payload = self.sale_payload()
        payload['items'].append({'producto_id': ves.pk, 'cantidad': 1})
        response = self.client_a.post('/api/store/ventas-presenciales/', payload, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(self.counts(), before)

    def test_conteo_sin_almacen_usa_principal_y_no_duplica_movimiento(self):
        transferir_stock(self.product, self.a1, self.a2, 4, self.owner_a)
        response = self.client_a.post(self.adjustment_url(), {'nuevo_stock': 7}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual((self.balance(self.a1), self.balance(self.a2), response.data['stock']), (7, 4, 11))
        before = self.counts()
        repeated = self.client_a.post(self.adjustment_url(), {'nuevo_stock': 7}, format='json')
        self.assertEqual(repeated.status_code, 200)
        self.assertIsNone(repeated.data['movimiento'])
        self.assertEqual(self.counts(), before)

    def test_transferencia_con_tercer_almacen_no_copia_stock_ni_deja_filas(self):
        third = Almacen.objects.create(sucursal=self.a1.sucursal, codigo='QA3', nombre='QA tercero')
        before = self.counts()
        response = self.client_a.post('/api/store/transferencias-inventario/', {
            'producto_id': self.product.pk, 'almacen_origen_id': self.a2.pk,
            'almacen_destino_id': third.pk, 'cantidad': 1,
        }, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.balance(self.a1), 10)

    def concurrent_posts(self, requests):
        barrier = Barrier(len(requests), timeout=15)

        def worker(request):
            close_old_connections()
            try:
                client = self.client_for(self.token_a)
                barrier.wait()
                response = client.post(request[0], request[1], format='json')
                return response.status_code
            finally:
                connections['default'].close()

        with ThreadPoolExecutor(max_workers=len(requests)) as pool:
            futures = [pool.submit(worker, request) for request in requests]
            return [future.result(timeout=30) for future in futures]

    def test_dos_cajas_compiten_por_ultima_unidad(self):
        response = self.client_a.post(self.adjustment_url(), {'nuevo_stock': 1}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        before_orders = StoreOrder.objects.count()
        request = ('/api/store/ventas-presenciales/', self.sale_payload())
        self.assertEqual(sorted(self.concurrent_posts([request, request])), [201, 400])
        self.assertEqual(StoreOrder.objects.count(), before_orders + 1)
        self.assertEqual(self.balance(self.a1), 0)

    def test_reintento_idempotente_con_stock_agotado_devuelve_comprobante_original(self):
        payload = {**self.sale_payload(10), 'clave_operacion': str(uuid4())}
        url = '/api/store/ventas-presenciales/operaciones/'
        first = self.client_a.post(url, payload, format='json')
        self.assertEqual(first.status_code, 201, first.data)
        counts = self.counts()
        self.product.precio = '9.00'
        self.product.save(update_fields=['precio'])
        retry = self.client_a.post(url, payload, format='json')
        self.assertEqual(retry.status_code, 200, retry.data)
        self.assertTrue(retry.data['repetida'])
        self.assertEqual(first.data['order'], retry.data['order'])
        self.assertEqual(first.data['movimientos'], retry.data['movimientos'])
        self.assertEqual(self.counts(), counts)
        self.assertEqual(self.balance(self.a1), 0)

    def test_dos_posts_misma_clave_crean_una_sola_venta(self):
        payload = {**self.sale_payload(), 'clave_operacion': str(uuid4())}
        request = ('/api/store/ventas-presenciales/operaciones/', payload)
        before = StoreOrder.objects.count()
        self.assertEqual(sorted(self.concurrent_posts([request, request])), [200, 201])
        self.assertEqual(StoreOrder.objects.count(), before + 1)
        self.assertEqual(self.balance(self.a1), 9)
        self.assertEqual(OperacionVentaPresencial.objects.count(), 1)

    def test_conflicto_clave_con_payload_distinto_no_descuenta(self):
        payload = {**self.sale_payload(), 'clave_operacion': str(uuid4())}
        url = '/api/store/ventas-presenciales/operaciones/'
        self.assertEqual(self.client_a.post(url, payload, format='json').status_code, 201)
        counts = self.counts()
        payload['items'][0]['cantidad'] = 2
        self.assertEqual(self.client_a.post(url, payload, format='json').status_code, 409)
        self.assertEqual(self.counts(), counts)

    def test_cancelacion_y_post_concurrentes_no_dejan_venta_duplicada(self):
        clave = str(uuid4())
        url = '/api/store/ventas-presenciales/operaciones/'
        payload = {**self.sale_payload(), 'clave_operacion': clave}
        statuses = self.concurrent_posts([(url, payload), (f'{url}{clave}/cancelar/', {})])
        self.assertEqual(statuses[1], 200)
        self.assertIn(statuses[0], (201, 409))
        operation = OperacionVentaPresencial.objects.get(tienda_id=self.store_a.pk, clave=clave)
        if operation.cancelada:
            self.assertIsNone(operation.respuesta)
            self.assertEqual(self.balance(self.a1), 10)
            self.assertEqual(self.client_a.post(url, payload, format='json').status_code, 409)
        else:
            self.assertIsNotNone(operation.respuesta)
            self.assertEqual(self.balance(self.a1), 9)
            self.assertEqual(self.client_a.post(url, payload, format='json').status_code, 200)

    def test_cancelar_venta_confirmada_no_la_anula(self):
        clave = str(uuid4())
        url = '/api/store/ventas-presenciales/operaciones/'
        sale = self.client_a.post(url, {**self.sale_payload(), 'clave_operacion': clave}, format='json')
        cancel = self.client_a.post(f'{url}{clave}/cancelar/', {}, format='json')
        self.assertEqual(cancel.status_code, 200, cancel.data)
        self.assertFalse(cancel.data['cancelada'])
        self.assertEqual(cancel.data['resultado']['order'], sale.data['order'])
        self.assertEqual(self.balance(self.a1), 9)

    def test_fallo_de_stock_revierte_operacion_y_permite_cancelar(self):
        clave = str(uuid4())
        url = '/api/store/ventas-presenciales/operaciones/'
        counts = self.counts()
        self.assertEqual(self.client_a.post(url, {**self.sale_payload(11), 'clave_operacion': clave}, format='json').status_code, 400)
        self.assertFalse(OperacionVentaPresencial.objects.filter(clave=clave).exists())
        self.assertEqual(self.counts(), counts)
        canceled = self.client_a.post(f'{url}{clave}/cancelar/', {}, format='json')
        self.assertTrue(canceled.data['cancelada'])

    def test_otra_tienda_no_recupera_ni_cancela_la_operacion_original(self):
        clave = str(uuid4())
        url = '/api/store/ventas-presenciales/operaciones/'
        payload = {**self.sale_payload(), 'clave_operacion': clave}
        sale = self.client_a.post(url, payload, format='json')
        self.assertEqual(sale.status_code, 201, sale.data)
        self.assertEqual(self.client_b.post(url, payload, format='json').status_code, 400)
        cancel = self.client_b.post(f'{url}{clave}/cancelar/', {}, format='json')
        self.assertTrue(cancel.data['cancelada'])
        operation = OperacionVentaPresencial.objects.get(tienda_id=self.store_a.pk, clave=clave)
        self.assertFalse(operation.cancelada)
        self.assertEqual(operation.respuesta['order']['id'], sale.data['order']['id'])
        for client in (APIClient(), self.client_customer):
            self.assertIn(client.post(url, payload, format='json').status_code, (401, 403))
            self.assertIn(client.post(f'{url}{clave}/cancelar/', {}, format='json').status_code, (401, 403))

    def test_deltas_simultaneos_se_acumulan(self):
        request = (self.adjustment_url(), {'delta': 1})
        self.assertEqual(self.concurrent_posts([request, request]), [200, 200])
        self.assertEqual(self.balance(self.a1), 12)

    def test_tickets_con_productos_en_orden_inverso(self):
        other = self.producto('QA segundo', 10)
        items = [{'producto_id': self.product.pk, 'cantidad': 1}, {'producto_id': other.pk, 'cantidad': 1}]
        self.assertEqual(self.concurrent_posts([
            ('/api/store/ventas-presenciales/', {'items': items}),
            ('/api/store/ventas-presenciales/', {'items': list(reversed(items))}),
        ]), [201, 201])
        self.assertEqual(self.balance(self.a1), 8)
        other.refresh_from_db()
        self.assertEqual(other.stock, 8)

    def test_transferencias_opuestas_conservan_saldos(self):
        transferir_stock(self.product, self.a1, self.a2, 5, self.owner_a)
        requests = [('/api/store/transferencias-inventario/', {
            'producto_id': self.product.pk, 'almacen_origen_id': origin.pk,
            'almacen_destino_id': destination.pk, 'cantidad': 1,
        }) for origin, destination in ((self.a1, self.a2), (self.a2, self.a1))]
        self.assertEqual(self.concurrent_posts(requests), [201, 201])
        self.assertEqual((self.balance(self.a1), self.balance(self.a2)), (5, 5))

    def test_diagnostico_detecta_discrepancia_sin_repararla(self):
        # Fixture deliberadamente inconsistente para probar sólo el diagnóstico.
        InventarioAlmacen.objects.filter(producto=self.product, almacen=self.a1).update(cantidad=9)
        before = self.counts()
        output = StringIO()
        call_command('diagnostico_inventario', stdout=output)
        report = json.loads(output.getvalue())
        self.assertTrue(report['solo_lectura'])
        self.assertEqual(report['inventario']['productos_con_total_inconsistente'], 1)
        self.assertEqual(self.counts(), before)
        self.product.refresh_from_db()
        self.assertEqual((self.product.stock, self.balance(self.a1)), (10, 9))
