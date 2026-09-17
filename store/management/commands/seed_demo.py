"""Seed de datos para testing manual del flujo TuPlaza.

Crea (idempotente) usuarios de prueba: admin, tienda, cliente, conductor.
Más: tienda con productos, categorías, tasa de cambio vigente, una orden
pending y una ServiceRequest de delivery pending sin conductor, lista para
que el conductor la tome desde el "Modo Conductor".

Uso:
    python manage.py seed_demo            # crea o actualiza
    python manage.py seed_demo --reset    # borra primero los usuarios demo
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from store.models import (
    Carrito,
    Categoria,
    DriverProfile,
    ProductoTienda,
    ServiceRequest,
    StoreOrder,
    TasaCambio,
    Tienda,
    Usuario,
    Wallet,
)


DEMO_PASSWORD = 'Tuplaza1'

# (Lagunillas, Zulia) -- coordenadas aproximadas para que el mapa renderice algo
PICKUP_COORDS = (Decimal('10.135'), Decimal('-71.260'))
DROPOFF_COORDS = (Decimal('10.150'), Decimal('-71.245'))

DEMO_USERS = {
    'admin': {
        'email': 'admin@tuplaza.test',
        'username': 'admin_demo',
        'first_name': 'Admin',
        'last_name': 'Demo',
        'rol': Usuario.ES_CLIENTE,
        'is_staff': True,
        'is_superuser': True,
    },
    'tienda': {
        'email': 'tienda@tuplaza.test',
        'username': 'tienda_demo',
        'first_name': 'Tienda',
        'last_name': 'Demo',
        'rol': Usuario.ES_TIENDA,
        'telefono': '+58 412 1234567',
    },
    'cliente': {
        'email': 'cliente@tuplaza.test',
        'username': 'cliente_demo',
        'first_name': 'Cliente',
        'last_name': 'Demo',
        'rol': Usuario.ES_CLIENTE,
        'telefono': '+58 414 7654321',
    },
    'conductor': {
        'email': 'conductor@tuplaza.test',
        'username': 'conductor_demo',
        'first_name': 'Conductor',
        'last_name': 'Demo',
        'rol': Usuario.ES_CONDUCTOR,
        'es_conductor': True,
        'telefono': '+58 416 9999999',
        'cedula_pasaporte': 'V-12345678',
    },
}


class Command(BaseCommand):
    help = 'Crea datos de prueba para testing manual del flujo de TuPlaza.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Borra primero los usuarios demo y todo lo asociado.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['reset']:
            self._reset()

        admin = self._upsert_user(DEMO_USERS['admin'])
        tienda_user = self._upsert_user(DEMO_USERS['tienda'])
        cliente = self._upsert_user(DEMO_USERS['cliente'])
        conductor = self._upsert_user(DEMO_USERS['conductor'])

        for user in (admin, tienda_user, cliente, conductor):
            Wallet.objects.get_or_create(usuario=user, defaults={'saldo': Decimal('50.00')})
            Carrito.objects.get_or_create(usuario=user)

        categoria = self._ensure_categoria()
        tienda = self._ensure_tienda(tienda_user)
        productos = self._ensure_productos(tienda, categoria)
        self._ensure_tasa_cambio(admin)
        driver_profile = self._ensure_driver_profile(conductor)
        store_order = self._ensure_demo_store_order(cliente, productos[0])
        service_request = self._ensure_demo_service_request(cliente, store_order)

        self.stdout.write(self.style.SUCCESS('\n=== Seed listo ==='))
        self._print_credentials()
        self.stdout.write(
            f"\nTienda: {tienda.nombre} (id={tienda.id}) con {len(productos)} productos."
        )
        self.stdout.write(
            f"DriverProfile: estado={driver_profile.estado}, "
            f"placa={driver_profile.vehiculo_placa}."
        )
        self.stdout.write(
            f"StoreOrder demo: #{store_order.id} estado={store_order.estado}."
        )
        self.stdout.write(
            f"ServiceRequest demo: #{service_request.id} tipo={service_request.tipo} "
            f"estado={service_request.estado} (sin conductor — el conductor demo puede tomarla)."
        )

    # ---------- helpers ----------

    def _reset(self):
        emails = [u['email'] for u in DEMO_USERS.values()]
        deleted, _ = Usuario.objects.filter(email__in=emails).delete()
        self.stdout.write(self.style.WARNING(f'Reset: {deleted} filas borradas.'))

    def _upsert_user(self, data: dict) -> Usuario:
        defaults = {k: v for k, v in data.items() if k != 'email'}
        user, created = Usuario.objects.get_or_create(
            email=data['email'],
            defaults=defaults,
        )
        if not created:
            # Actualiza campos por si cambiamos el seed
            for key, value in defaults.items():
                setattr(user, key, value)
        user.set_password(DEMO_PASSWORD)
        user.save()
        action = 'creado' if created else 'actualizado'
        self.stdout.write(f'  Usuario {action}: {user.email} (rol={user.rol})')
        return user

    def _ensure_categoria(self) -> Categoria:
        cat, _ = Categoria.objects.get_or_create(
            nombre='Comida',
            defaults={
                'descripcion': 'Categoría demo para productos de comida.',
                'tipo': Categoria.TIPO_PRODUCTO,
                'es_comida': True,
            },
        )
        if not cat.es_comida:
            cat.es_comida = True
            cat.save(update_fields=['es_comida'])
        return cat

    def _ensure_tienda(self, usuario: Usuario) -> Tienda:
        tienda, _ = Tienda.objects.get_or_create(
            usuario=usuario,
            defaults={
                'nombre': 'KW Kitchen Demo',
                'direccion': 'Lagunillas, Zulia, Venezuela',
                'telefono': usuario.telefono or '+58 412 1234567',
                'ubicacion_lat': PICKUP_COORDS[0],
                'ubicacion_lng': PICKUP_COORDS[1],
            },
        )
        return tienda

    def _ensure_productos(self, tienda: Tienda, categoria: Categoria):
        seed_products = [
            ('Hamburguesa clásica', 'Carne, queso, lechuga y tomate.', Decimal('5.00'), 20),
            ('Pizza personal', 'Margarita o pepperoni.', Decimal('6.50'), 15),
            ('Empanadas (x3)', 'Carne mechada o pollo.', Decimal('3.00'), 30),
            ('Refresco 500ml', 'Coca-Cola, Pepsi o limonada natural.', Decimal('1.50'), 50),
        ]
        productos = []
        for nombre, descripcion, precio, stock in seed_products:
            prod, _ = ProductoTienda.objects.get_or_create(
                tienda=tienda,
                nombre=nombre,
                defaults={
                    'descripcion': descripcion,
                    'precio': precio,
                    'stock': stock,
                    'moneda': 'USD',
                    'categoria': categoria,
                },
            )
            productos.append(prod)
        return productos

    def _ensure_tasa_cambio(self, registrado_por: Usuario):
        if not TasaCambio.objects.exists():
            TasaCambio.objects.create(
                valor_bs=Decimal('40.0000'),
                fuente=TasaCambio.FUENTE_MANUAL,
                registrado_por=registrado_por,
            )

    def _ensure_driver_profile(self, conductor: Usuario) -> DriverProfile:
        # Update siempre los campos: si ya existía sin licencia/placa/etc el seed
        # los completa para que is_complete pase.
        fields = {
            'licencia_numero': 'LIC-DEMO-001',
            'vehiculo_tipo': DriverProfile.VEHICULO_MOTO,
            'vehiculo_placa': 'AB123CD',
            'vehiculo_color': 'Negro',
            'capacidad_paquetes': 2,
            'ubicacion_lat': PICKUP_COORDS[0],
            'ubicacion_lng': PICKUP_COORDS[1],
        }
        profile, created = DriverProfile.objects.get_or_create(
            usuario=conductor,
            defaults={**fields, 'estado': DriverProfile.ESTADO_OFFLINE},
        )
        if not created:
            for key, value in fields.items():
                setattr(profile, key, value)
            profile.save()
        return profile

    def _ensure_demo_store_order(self, cliente: Usuario, producto: ProductoTienda) -> StoreOrder:
        order = StoreOrder.objects.filter(
            usuario=cliente,
            producto=producto,
            estado=StoreOrder.ESTADO_PENDIENTE,
        ).first()
        if order:
            return order
        cantidad = 1
        return StoreOrder.objects.create(
            usuario=cliente,
            producto=producto,
            cantidad=cantidad,
            precio_unitario=producto.precio,
            total=producto.precio * cantidad,
            moneda=producto.moneda,
            estado=StoreOrder.ESTADO_PENDIENTE,
            direccion_entrega='Ciudad Ojeda, Lagunillas, Zulia',
            notas='Pedido generado por seed_demo.',
        )

    def _ensure_demo_service_request(self, cliente: Usuario, store_order: StoreOrder) -> ServiceRequest:
        existing = ServiceRequest.objects.filter(
            cliente=cliente,
            store_order=store_order,
            estado=ServiceRequest.ESTADO_PENDIENTE,
        ).first()
        if existing:
            return existing
        return ServiceRequest.objects.create(
            tipo=ServiceRequest.TIPO_DELIVERY,
            cliente=cliente,
            store_order=store_order,
            pickup_direccion='KW Kitchen Demo, Lagunillas, Zulia',
            pickup_lat=PICKUP_COORDS[0],
            pickup_lng=PICKUP_COORDS[1],
            dropoff_direccion='Ciudad Ojeda, Lagunillas, Zulia',
            dropoff_lat=DROPOFF_COORDS[0],
            dropoff_lng=DROPOFF_COORDS[1],
            distancia_metros=2200,
            duracion_segundos=300,
            costo_estimado=Decimal('3.00'),
            estado=ServiceRequest.ESTADO_PENDIENTE,
            notas='Solicitud demo lista para asignar a un conductor.',
        )

    def _print_credentials(self):
        self.stdout.write(self.style.HTTP_INFO('\nCredenciales demo (password: Tuplaza1):'))
        for key, data in DEMO_USERS.items():
            self.stdout.write(f"  {key:9s} -> {data['email']}")
