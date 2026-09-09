"""Smoke sin credenciales ni escrituras sobre datos reales.

Uso: python3 scripts/smoke_inventory_routes.py https://host-de-la-api
Sólo comprueba disponibilidad y rechazo de solicitudes anónimas.
"""
import argparse
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base_url')
    parser.add_argument('--expected-revision', help='SHA completo esperado en Railway.')
    args = parser.parse_args()
    base = args.base_url.rstrip('/')
    cases = [
        ('GET', '/', 200),
        ('GET', '/api/store/mi-negocio/', 401),
        ('GET', '/api/store/inventario-almacenes/?producto=0&almacen=0', 401),
        ('GET', '/api/store/transferencias-inventario/', 401),
        ('GET', '/api/store/productos-tienda/0/movimientos/', 401),
        ('GET', '/api/store/productos-tienda/0/movimientos/?paginado=1&almacen_id=1&origen=ajuste_manual&dias=30', 401),
        ('POST', '/api/store/transferencias-inventario/', 401),
        ('POST', '/api/store/ventas-presenciales/', 401),
        ('GET', '/api/store/ventas-presenciales/operaciones/', 401),
        ('POST', '/api/store/ventas-presenciales/operaciones/', 401),
        ('POST', '/api/store/ventas-presenciales/operaciones/00000000-0000-4000-8000-000000000000/cancelar/', 401),
        ('POST', '/api/store/productos-tienda/0/ajustar-stock/', 401),
        ('GET', '/api/store/cajas/sesiones/', 401),
        ('GET', '/api/store/cajas/sesiones/0/', 401),
        ('GET', '/api/store/cajas/ventas/', 401),
        ('POST', '/api/store/cajas/ventas/', 401),
        ('POST', '/api/store/cajas/operaciones/', 401),
        ('POST', '/api/store/cajas/operaciones/00000000-0000-4000-8000-000000000000/cancelar/', 401),
    ]
    for method, path, expected in cases:
        request = Request(base + path, method=method,
                          data=b'{}' if method == 'POST' else None,
                          headers={'Content-Type': 'application/json'})
        try:
            response = urlopen(request, timeout=20)
        except HTTPError as error:
            response = error
        with response:
            status = response.code
            body = json.load(response)
        print(f'{method} {path}: {status} (esperado {expected})', flush=True)
        if status != expected:
            raise SystemExit('Falló el smoke de inventario.')
        if path == '/' and body.get('status') != 'ok':
            raise SystemExit('La API no indica estado saludable.')
        if path == '/' and args.expected_revision:
            if body.get('revision') != args.expected_revision.lower():
                raise SystemExit('La API todavía no confirma la revisión esperada.')
            print('Revisión desplegada confirmada.', flush=True)
        if expected == 401 and 'detail' not in body:
            raise SystemExit('La respuesta de autenticación no tiene el contrato esperado.')


if __name__ == '__main__':
    main()
