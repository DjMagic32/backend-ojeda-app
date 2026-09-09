"""Smoke sin credenciales ni escrituras sobre datos reales.

Uso: python3 scripts/smoke_inventory_routes.py https://host-de-la-api
Sólo comprueba disponibilidad y rechazo de solicitudes anónimas.
"""
import json
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main():
    base = sys.argv[1].rstrip('/')
    cases = [
        ('GET', '/', 200),
        ('GET', '/api/store/mi-negocio/', 401),
        ('GET', '/api/store/inventario-almacenes/?producto=0&almacen=0', 401),
        ('GET', '/api/store/transferencias-inventario/', 401),
        ('GET', '/api/store/productos-tienda/0/movimientos/', 401),
        ('POST', '/api/store/transferencias-inventario/', 401),
        ('POST', '/api/store/ventas-presenciales/', 401),
        ('POST', '/api/store/productos-tienda/0/ajustar-stock/', 401),
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
        if expected == 401 and 'detail' not in body:
            raise SystemExit('La respuesta de autenticación no tiene el contrato esperado.')


if __name__ == '__main__':
    main()
