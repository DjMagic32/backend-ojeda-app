import logging
import unicodedata
from decimal import Decimal, InvalidOperation
from math import asin, cos, radians, sin, sqrt
from typing import Iterable, Optional, Type

import graphene
from graphene import Enum
from graphql import GraphQLError
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from store.services.mail import send_app_email
from django.db import transaction
from django.db.models import Q, QuerySet, Sum
from django.utils import timezone
from django.utils.crypto import get_random_string
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)

from store.models import (
    Carrito,
    Conversation,
    DriverProfile,
    Lugar,
    Notificacion,
    PasswordResetCode,
    ProductoTienda,
    ServiceRequest,
    ServiceRequestCandidate,
    StoreOrder,
    StoreOrderItem,
    StoreOrderReview,
    StoreOrderSellerReview,
    TarifaDelivery,
    TasaCambio,
    Tienda,
    Usuario,
)
from .types import (
    DriverProfileType,
    DestinoRecienteType,
    LugarBusquedaType,
    LugarType,
    ProductoTiendaType,
    TarifaDeliveryType,
    ServiceRequestType,
    StoreOrderReviewType,
    StoreOrderSellerReviewType,
    StoreOrderType,
    UsuarioType,
)
from store.services.mapbox import (
    MapboxConfigurationError,
    extract_route_summary,
    fetch_directions,
)
from store.services.pricing import calcular_costo_delivery, haversine_metros
from store.services.openstreetmap_places import buscar_lugares_openstreetmap


class ProductScopeEnum(Enum):
    ALL = "all"
    MINE = "mine"


class ProductoTipoEnum(Enum):
    PRODUCTO = ProductoTienda.TIPO_PRODUCTO
    SERVICIO = ProductoTienda.TIPO_SERVICIO


class UsuarioRolEnum(Enum):
    CLIENTE = Usuario.ES_CLIENTE
    TIENDA = Usuario.ES_TIENDA
    CONDUCTOR = Usuario.ES_CONDUCTOR


class StoreOrderScopeEnum(Enum):
    MINE = "mine"
    STORE = "store"


class StoreOrderStatusEnum(Enum):
    PENDING = StoreOrder.ESTADO_PENDIENTE
    ONGOING = StoreOrder.ESTADO_EN_CURSO
    COMPLETED = StoreOrder.ESTADO_COMPLETADO
    CANCELLED = StoreOrder.ESTADO_CANCELADO


class ServiceRequestTypeEnum(Enum):
    TAXI = ServiceRequest.TIPO_TAXI
    DELIVERY = ServiceRequest.TIPO_DELIVERY


class ServiceRequestStatusEnum(Enum):
    PENDING = ServiceRequest.ESTADO_PENDIENTE
    ASSIGNED = ServiceRequest.ESTADO_ASIGNADO
    ARRIVED_PICKUP = ServiceRequest.ESTADO_LLEGO_RECOGIDA
    IN_PROGRESS = ServiceRequest.ESTADO_EN_CURSO
    ARRIVED_DROPOFF = ServiceRequest.ESTADO_LLEGO_DESTINO
    COMPLETED = ServiceRequest.ESTADO_COMPLETADO
    CANCELLED = ServiceRequest.ESTADO_CANCELADO


class DriverStatusEnum(Enum):
    OFFLINE = DriverProfile.ESTADO_OFFLINE
    AVAILABLE = DriverProfile.ESTADO_DISPONIBLE
    ON_TRIP = DriverProfile.ESTADO_EN_VIAJE


class ServiceRequestScopeEnum(Enum):
    CLIENT = "client"
    DRIVER = "driver"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_km = 6371.0
    rlat1, rlat2 = radians(lat1), radians(lat2)
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(rlat1) * cos(rlat2) * sin(dlon / 2) ** 2
    return 2 * earth_radius_km * asin(sqrt(a))


def _normalize_place_text(value: str) -> str:
    decomposed = unicodedata.normalize('NFKD', value or '')
    without_accents = ''.join(
        character for character in decomposed
        if not unicodedata.combining(character)
    )
    return ' '.join(without_accents.casefold().split())


def _normalize_scope(scope_value, enum_cls: Type[Enum], default_value: str) -> str:
    if scope_value is None:
        return default_value
    if hasattr(scope_value, "value"):
        return scope_value.value  # Graphene enum instance
    normalized = str(scope_value).lower()
    allowed = {member.value for member in enum_cls}
    if normalized not in allowed:
        raise GraphQLError("Valor de scope inválido")
    return normalized


def _normalize_status_list(
    status_values: Optional[Iterable[StoreOrderStatusEnum]],
) -> Optional[list[str]]:
    if status_values is None:
        return None

    normalized_values: list[str] = []
    allowed = {member.value for member in StoreOrderStatusEnum}

    for value in status_values:
        candidate = value.value if hasattr(value, "value") else str(value).lower()
        if candidate not in allowed:
            raise GraphQLError("Estado de orden inválido")
        normalized_values.append(candidate)

    return normalized_values


def _normalize_service_status_list(
    status_values: Optional[Iterable[ServiceRequestStatusEnum]],
) -> Optional[list[str]]:
    if status_values is None:
        return None

    normalized_values: list[str] = []
    allowed = {member.value for member in ServiceRequestStatusEnum}

    for value in status_values:
        candidate = value.value if hasattr(value, "value") else str(value).lower()
        if candidate not in allowed:
            raise GraphQLError("Estado de solicitud inválido")
        normalized_values.append(candidate)

    return normalized_values


class Query(graphene.ObjectType):
    me = graphene.Field(UsuarioType)
    store_products = graphene.List(
        ProductoTiendaType,
        scope=graphene.Argument(ProductScopeEnum, default_value=ProductScopeEnum.ALL),
        tienda_id=graphene.ID(),
        categoria_id=graphene.ID(),
        precio_min=graphene.Float(),
        precio_max=graphene.Float(),
        search=graphene.String(),
        tipo=graphene.Argument(ProductoTipoEnum),
        user_lat=graphene.Float(),
        user_lng=graphene.Float(),
        radio_km=graphene.Float(),
    )
    store_product = graphene.Field(
        ProductoTiendaType,
        id=graphene.ID(required=True),
    )
    store_orders = graphene.List(
        StoreOrderType,
        scope=graphene.Argument(StoreOrderScopeEnum, default_value=StoreOrderScopeEnum.MINE),
        estados=graphene.List(StoreOrderStatusEnum),
    )
    service_requests = graphene.List(
        ServiceRequestType,
        scope=graphene.Argument(ServiceRequestScopeEnum, default_value=ServiceRequestScopeEnum.CLIENT),
        estados=graphene.List(ServiceRequestStatusEnum),
        incluir_pendientes_sin_driver=graphene.Boolean(default_value=False),
    )
    service_request = graphene.Field(
        ServiceRequestType,
        id=graphene.ID(required=True),
    )
    my_driver_profile = graphene.Field(DriverProfileType)
    delivery_tarifas = graphene.Field(TarifaDeliveryType)
    store_product_by_barcode = graphene.Field(
        ProductoTiendaType,
        codigo=graphene.String(required=True),
    )
    lugares_cercanos = graphene.List(
        LugarType,
        query=graphene.String(),
        lat=graphene.Float(required=True),
        lng=graphene.Float(required=True),
        limit=graphene.Int(default_value=8),
    )
    lugares_openstreetmap = graphene.List(
        LugarBusquedaType,
        query=graphene.String(),
        lat=graphene.Float(required=True),
        lng=graphene.Float(required=True),
        limit=graphene.Int(default_value=8),
    )
    destinos_recientes = graphene.List(
        DestinoRecienteType,
        limit=graphene.Int(default_value=3),
    )

    def resolve_delivery_tarifas(self, info):
        return TarifaDelivery.vigente()

    def resolve_lugares_cercanos(
        self,
        info,
        query: Optional[str] = None,
        lat: float = 0,
        lng: float = 0,
        limit: int = 8,
    ):
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            raise GraphQLError('Las coordenadas de búsqueda no son válidas')

        limit = max(1, min(limit or 8, 30))
        normalized_query = _normalize_place_text(query or '')
        tokens = normalized_query.split()
        places = Lugar.objects.filter(activo=True)
        matches = []

        for place in places:
            searchable = _normalize_place_text(
                ' '.join((place.nombre, place.alias, place.direccion, place.categoria))
            )
            if tokens and not all(token in searchable for token in tokens):
                continue
            distance = _haversine_km(lat, lng, float(place.lat), float(place.lng))
            place._distancia_km = round(distance, 3)
            matches.append(place)

        return sorted(
            matches,
            key=lambda place: (place._distancia_km, place.nombre.casefold()),
        )[:limit]

    def resolve_lugares_openstreetmap(
        self,
        info,
        query: Optional[str] = None,
        lat: float = 0,
        lng: float = 0,
        limit: int = 8,
    ):
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            raise GraphQLError('Las coordenadas de búsqueda no son válidas')
        return buscar_lugares_openstreetmap(query, lat, lng, limit)

    def resolve_destinos_recientes(self, info, limit: int = 3):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError('Autenticación requerida')

        limit = max(1, min(limit or 3, 3))
        servicios = ServiceRequest.objects.filter(
            cliente=user,
            estado=ServiceRequest.ESTADO_COMPLETADO,
            dropoff_lat__isnull=False,
            dropoff_lng__isnull=False,
        ).order_by('-completado_en', '-id')

        destinos = []
        vistos = set()
        for servicio in servicios.iterator():
            coordenadas = (servicio.dropoff_lat, servicio.dropoff_lng)
            if coordenadas in vistos:
                continue

            direccion = (servicio.dropoff_direccion or '').strip()
            nombre = direccion.split(',', 1)[0].strip() or 'Destino en el mapa'
            destinos.append({
                'id': str(servicio.id),
                'nombre': nombre,
                'direccion': direccion,
                'lat': float(servicio.dropoff_lat),
                'lng': float(servicio.dropoff_lng),
                'ultima_vez': servicio.completado_en or servicio.actualizado,
            })
            vistos.add(coordenadas)
            if len(destinos) >= limit:
                break

        return destinos

    def resolve_store_product_by_barcode(self, info, codigo):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Autenticación requerida")
        if getattr(user, 'rol', None) != Usuario.ES_TIENDA:
            raise GraphQLError("Solo las tiendas pueden buscar por código de barras")
        codigo = (codigo or '').strip()
        if not codigo:
            return None
        return (
            ProductoTienda.objects.select_related('tienda')
            .filter(tienda__usuario=user, codigo_barras=codigo)
            .first()
        )

    def resolve_me(self, info):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Autenticación requerida")
        return user

    def resolve_store_products(
        self,
        info,
        scope=ProductScopeEnum.ALL,
        tienda_id: Optional[int] = None,
        categoria_id: Optional[int] = None,
        precio_min: Optional[float] = None,
        precio_max: Optional[float] = None,
        search: Optional[str] = None,
        tipo: Optional[ProductoTipoEnum] = None,
        user_lat: Optional[float] = None,
        user_lng: Optional[float] = None,
        radio_km: Optional[float] = None,
    ):
        scope_value = _normalize_scope(scope, ProductScopeEnum, ProductScopeEnum.ALL.value)
        queryset: QuerySet[ProductoTienda] = ProductoTienda.objects.select_related(
            "tienda",
            "tienda__usuario",
            "categoria",
        )

        if scope_value == ProductScopeEnum.MINE.value:
            user = info.context.user
            if not user or not user.is_authenticated:
                raise GraphQLError("Autenticación requerida para ver tus productos")
            if getattr(user, "rol", None) != Usuario.ES_TIENDA:
                raise GraphQLError("Solo los usuarios con rol TIENDA pueden ver sus productos")
            try:
                tienda = Tienda.objects.get(usuario=user)
            except Tienda.DoesNotExist:
                return []
            queryset = queryset.filter(tienda=tienda)

        if tienda_id is not None:
            queryset = queryset.filter(tienda_id=tienda_id)

        if categoria_id is not None:
            queryset = queryset.filter(categoria_id=categoria_id)

        if tipo is not None:
            tipo_value = tipo.value if hasattr(tipo, "value") else str(tipo)
            queryset = queryset.filter(tipo=tipo_value)

        if precio_min is not None:
            try:
                queryset = queryset.filter(precio__gte=Decimal(str(precio_min)))
            except (InvalidOperation, ValueError) as exc:
                raise GraphQLError("precio_min inválido") from exc

        if precio_max is not None:
            try:
                queryset = queryset.filter(precio__lte=Decimal(str(precio_max)))
            except (InvalidOperation, ValueError) as exc:
                raise GraphQLError("precio_max inválido") from exc

        if search:
            term = search.strip()
            if term:
                queryset = queryset.filter(
                    Q(nombre__icontains=term) | Q(descripcion__icontains=term)
                )

        distance_active = (
            user_lat is not None and user_lng is not None and radio_km is not None
        )
        if distance_active:
            if radio_km <= 0:
                raise GraphQLError("radio_km debe ser mayor a cero")
            queryset = queryset.filter(
                tienda__ubicacion_lat__isnull=False,
                tienda__ubicacion_lng__isnull=False,
            )
            productos = list(queryset)
            filtered = []
            for producto in productos:
                t_lat = producto.tienda.ubicacion_lat
                t_lng = producto.tienda.ubicacion_lng
                distancia = _haversine_km(
                    float(user_lat),
                    float(user_lng),
                    float(t_lat),
                    float(t_lng),
                )
                if distancia <= radio_km:
                    filtered.append(producto)
            return filtered

        return list(queryset)

    def resolve_store_product(self, info, id: int):
        try:
            return ProductoTienda.objects.select_related(
                "tienda",
                "tienda__usuario",
            ).get(pk=id)
        except ProductoTienda.DoesNotExist as exc:
            raise GraphQLError("Producto no encontrado") from exc

    def resolve_store_orders(self, info, scope=StoreOrderScopeEnum.MINE, estados=None):
        scope_value = _normalize_scope(scope, StoreOrderScopeEnum, StoreOrderScopeEnum.MINE.value)
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Autenticación requerida")

        base_queryset: QuerySet[StoreOrder] = StoreOrder.objects.select_related(
            "producto",
            "producto__tienda",
            "producto__tienda__usuario",
            "usuario",
            "seller_review",
            "seller_review__tienda",
            "seller_review__comprador",
        )

        if estados:
            normalized_status_list = _normalize_status_list(estados)
            if normalized_status_list:
                base_queryset = base_queryset.filter(estado__in=normalized_status_list)

        if scope_value == StoreOrderScopeEnum.STORE.value:
            if getattr(user, "rol", None) != Usuario.ES_TIENDA:
                raise GraphQLError("Solo las tiendas pueden consultar órdenes de su tienda")
            return list(base_queryset.filter(producto__tienda__usuario=user))

        return list(base_queryset.filter(usuario=user))

    def resolve_service_requests(
        self,
        info,
        scope=ServiceRequestScopeEnum.CLIENT,
        estados=None,
        incluir_pendientes_sin_driver: bool = False,
    ):
        scope_value = _normalize_scope(scope, ServiceRequestScopeEnum, ServiceRequestScopeEnum.CLIENT.value)
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Autenticación requerida")

        base_queryset: QuerySet[ServiceRequest] = ServiceRequest.objects.select_related(
            "cliente",
            "driver",
            "store_order",
            "store_order__producto",
            "store_order__producto__tienda",
        )

        if estados:
            normalized_status_list = _normalize_service_status_list(estados)
            if normalized_status_list:
                base_queryset = base_queryset.filter(estado__in=normalized_status_list)

        if scope_value == ServiceRequestScopeEnum.DRIVER.value:
            if not getattr(user, "es_conductor", False):
                raise GraphQLError("Solo los conductores pueden ver sus servicios")

            driver_qs = base_queryset.filter(driver=user)
            if incluir_pendientes_sin_driver:
                pendientes_disponibles = base_queryset.filter(
                    driver__isnull=True,
                    estado=ServiceRequest.ESTADO_PENDIENTE,
                ).exclude(cliente=user).exclude(
                    candidates__driver=user,
                )
                pendientes_postulados = base_queryset.filter(
                    driver__isnull=True,
                    estado=ServiceRequest.ESTADO_PENDIENTE,
                    candidates__driver=user,
                    candidates__estado=ServiceRequestCandidate.ESTADO_POSTULADO,
                ).exclude(cliente=user)
                driver_qs = (
                    driver_qs | pendientes_disponibles | pendientes_postulados
                )
            return list(driver_qs.distinct())

        return list(base_queryset.filter(cliente=user))

    def resolve_my_driver_profile(self, info):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Autenticación requerida")
        try:
            return user.perfil_conductor
        except DriverProfile.DoesNotExist:
            return None

    def resolve_service_request(self, info, id: int):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Autenticación requerida")
        try:
            servicio = ServiceRequest.objects.select_related(
                "cliente",
                "driver",
                "store_order",
                "store_order__producto",
                "store_order__producto__tienda",
            ).get(pk=id)
        except ServiceRequest.DoesNotExist as exc:
            raise GraphQLError("Solicitud no encontrada") from exc

        es_comprador_orden = (
            servicio.store_order is not None
            and servicio.store_order.usuario_id == user.id
        )
        if (
            servicio.cliente_id != user.id
            and servicio.driver_id != user.id
            and not es_comprador_orden
            and not ServiceRequestCandidate.objects.filter(
                service_request=servicio,
                driver=user,
                estado=ServiceRequestCandidate.ESTADO_POSTULADO,
            ).exists()
        ):
            raise GraphQLError("No tienes permiso para ver esta solicitud")

        return servicio


class Login(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)
        password = graphene.String(required=True)

    access_token = graphene.String()
    refresh_token = graphene.String()
    user = graphene.Field(UsuarioType)

    @staticmethod
    def mutate(root, info, email: str, password: str):
        normalized_email = email.strip().lower()
        user = authenticate(request=info.context, username=normalized_email, password=password)
        if user is None:
            raise GraphQLError("Credenciales inválidas")
        if not user.is_active:
            raise GraphQLError("La cuenta está inactiva")

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        return Login(access_token=access_token, refresh_token=refresh_token, user=user)


def _validar_stock_producto(producto: ProductoTienda, cantidad: int) -> None:
    if (
        producto.tipo == ProductoTienda.TIPO_PRODUCTO
        and producto.stock is not None
        and not producto.permite_encargo
    ):
        comprometido = (
            StoreOrderItem.objects.filter(
                producto=producto,
                order__estado__in=[
                    StoreOrder.ESTADO_PENDIENTE,
                    StoreOrder.ESTADO_EN_CURSO,
                ],
            ).aggregate(total=Sum('cantidad'))['total']
            or 0
        )
        disponible = max(producto.stock - comprometido, 0)
        if cantidad > disponible:
            if disponible == 0:
                raise GraphQLError(
                    f"'{producto.nombre}' no tiene stock disponible por ahora. "
                    "La tienda no acepta pedidos por encargo para este producto."
                )
            raise GraphQLError(
                f"Stock insuficiente de '{producto.nombre}': solo quedan "
                f"{disponible} unidad(es) disponibles."
            )


class CreateStoreOrder(graphene.Mutation):
    class Arguments:
        producto_id = graphene.ID(required=True)
        cantidad = graphene.Int(required=False, default_value=1)
        direccion_entrega = graphene.String(required=False)
        notas = graphene.String(required=False)

    order = graphene.Field(StoreOrderType)

    @staticmethod
    def mutate(
        root,
        info,
        producto_id: int,
        cantidad: int = 1,
        direccion_entrega: Optional[str] = None,
        notas: Optional[str] = None,
    ):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Autenticación requerida")

        if cantidad <= 0:
            raise GraphQLError("La cantidad debe ser mayor a cero")

        try:
            producto = ProductoTienda.objects.get(pk=producto_id)
        except ProductoTienda.DoesNotExist as exc:
            raise GraphQLError("Producto no encontrado") from exc

        _validar_stock_producto(producto, cantidad)

        precio_unitario: Decimal = producto.precio
        total = precio_unitario * Decimal(cantidad)
        tasa = TasaCambio.vigente()

        with transaction.atomic():
            order = StoreOrder.objects.create(
                usuario=user,
                producto=producto,
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                total=total,
                moneda=producto.moneda,
                tasa_aplicada=tasa.valor_bs if tasa else None,
                estado=StoreOrder.ESTADO_PENDIENTE,
                direccion_entrega=direccion_entrega,
                notas=notas,
            )
            StoreOrderItem.objects.create(
                order=order,
                producto=producto,
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                subtotal=total,
            )

        return CreateStoreOrder(order=order)


class CheckoutCart(graphene.Mutation):
    class Arguments:
        direccion_entrega = graphene.String(required=False)
        notas = graphene.String(required=False)

    orders = graphene.List(StoreOrderType)

    @staticmethod
    def mutate(
        root,
        info,
        direccion_entrega: Optional[str] = None,
        notas: Optional[str] = None,
    ):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Autenticación requerida")

        carrito = Carrito.objects.filter(usuario=user).first()
        items = (
            list(carrito.items.select_related("producto_tienda__tienda"))
            if carrito
            else []
        )
        items = [item for item in items if item.producto_tienda_id]
        if not items:
            raise GraphQLError("Tu carrito está vacío")

        for item in items:
            _validar_stock_producto(item.producto_tienda, item.cantidad)

        tasa = TasaCambio.vigente()

        # Una orden por combinación tienda+moneda: cada tienda cobra y
        # despacha por separado.
        grupos: dict = {}
        for item in items:
            clave = (item.producto_tienda.tienda_id, item.producto_tienda.moneda)
            grupos.setdefault(clave, []).append(item)

        orders = []
        with transaction.atomic():
            for (_tienda_id, moneda), grupo in grupos.items():
                total = sum(
                    (item.producto_tienda.precio * item.cantidad for item in grupo),
                    Decimal('0'),
                )
                order = StoreOrder.objects.create(
                    usuario=user,
                    producto=grupo[0].producto_tienda,
                    cantidad=sum(item.cantidad for item in grupo),
                    precio_unitario=grupo[0].producto_tienda.precio,
                    total=total,
                    moneda=moneda,
                    tasa_aplicada=tasa.valor_bs if tasa else None,
                    estado=StoreOrder.ESTADO_PENDIENTE,
                    direccion_entrega=direccion_entrega,
                    notas=notas,
                )
                StoreOrderItem.objects.bulk_create(
                    StoreOrderItem(
                        order=order,
                        producto=item.producto_tienda,
                        cantidad=item.cantidad,
                        precio_unitario=item.producto_tienda.precio,
                        subtotal=item.producto_tienda.precio * item.cantidad,
                    )
                    for item in grupo
                )
                orders.append(order)
            carrito.items.all().delete()

        return CheckoutCart(orders=orders)


class UpdateStoreOrderStatus(graphene.Mutation):
    class Arguments:
        order_id = graphene.ID(required=True)
        estado = graphene.Argument(StoreOrderStatusEnum, required=True)

    order = graphene.Field(StoreOrderType)

    @staticmethod
    def mutate(root, info, order_id: int, estado: StoreOrderStatusEnum):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Autenticación requerida")

        if getattr(user, "rol", None) != Usuario.ES_TIENDA:
            raise GraphQLError("Solo las tiendas pueden actualizar el estado de la orden")

        try:
            order = StoreOrder.objects.select_related(
                "producto",
                "producto__tienda",
                "producto__tienda__usuario",
            ).get(pk=order_id)
        except StoreOrder.DoesNotExist as exc:
            raise GraphQLError("Orden no encontrada") from exc

        if order.producto.tienda.usuario_id != user.id:
            raise GraphQLError("No puedes actualizar órdenes de otra tienda")

        normalized_status = (
            estado.value if hasattr(estado, "value") else str(estado).lower()
        )

        allowed_statuses = {member.value for member in StoreOrderStatusEnum}
        if normalized_status not in allowed_statuses:
            raise GraphQLError("Estado de orden inválido")

        if order.estado == normalized_status:
            return UpdateStoreOrderStatus(order=order)

        order.estado = normalized_status
        order.save(update_fields=["estado", "actualizado"])
        return UpdateStoreOrderStatus(order=order)


class CreateStoreOrderReview(graphene.Mutation):
    class Arguments:
        order_id = graphene.ID(required=True)
        rating = graphene.Int(required=True)
        comentario = graphene.String(required=False)

    review = graphene.Field(StoreOrderReviewType)

    @staticmethod
    def mutate(root, info, order_id: int, rating: int, comentario: Optional[str] = None):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Autenticación requerida")

        if rating < 1 or rating > 5:
            raise GraphQLError("La calificación debe estar entre 1 y 5")

        try:
            order = StoreOrder.objects.select_related(
                "producto",
                "producto__tienda",
            ).get(pk=order_id, usuario=user)
        except StoreOrder.DoesNotExist as exc:
            raise GraphQLError("No se encontró la orden solicitada") from exc

        if order.estado != StoreOrder.ESTADO_COMPLETADO:
            raise GraphQLError("Solo puedes evaluar órdenes completadas")

        if hasattr(order, "review"):
            raise GraphQLError("Ya enviaste una reseña para esta orden")

        review = StoreOrderReview.objects.create(
            order=order,
            producto=order.producto,
            usuario=user,
            rating=rating,
            comentario=comentario,
        )

        return CreateStoreOrderReview(review=review)


class CreateStoreOrderSellerReview(graphene.Mutation):
    class Arguments:
        order_id = graphene.ID(required=True)
        rating = graphene.Int(required=True)
        comentario = graphene.String(required=False)

    review = graphene.Field(StoreOrderSellerReviewType)

    @staticmethod
    def mutate(root, info, order_id: int, rating: int, comentario: Optional[str] = None):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Autenticación requerida")

        if getattr(user, "rol", None) != Usuario.ES_TIENDA:
            raise GraphQLError("Solo las tiendas pueden evaluar a los compradores")

        if rating < 1 or rating > 5:
            raise GraphQLError("La calificación debe estar entre 1 y 5")

        try:
            order = StoreOrder.objects.select_related(
                "producto",
                "producto__tienda",
            ).get(pk=order_id)
        except StoreOrder.DoesNotExist as exc:
            raise GraphQLError("Orden no encontrada") from exc

        if order.producto.tienda.usuario_id != user.id:
            raise GraphQLError("No puedes evaluar compradores de otra tienda")

        if order.estado != StoreOrder.ESTADO_COMPLETADO:
            raise GraphQLError("Solo puedes evaluar órdenes completadas")

        if hasattr(order, "seller_review"):
            raise GraphQLError("Ya evaluaste a este comprador")

        review = StoreOrderSellerReview.objects.create(
            order=order,
            tienda=order.producto.tienda,
            comprador=order.usuario,
            rating=rating,
            comentario=comentario,
        )

        return CreateStoreOrderSellerReview(review=review)


class RegisterDriver(graphene.Mutation):
    class Arguments:
        licencia_numero = graphene.String(required=False)
        vehiculo_tipo = graphene.String(required=False)
        vehiculo_placa = graphene.String(required=False)
        vehiculo_color = graphene.String(required=False)
        capacidad_paquetes = graphene.Int(required=False)
        telefono = graphene.String(required=False)
        cedula_pasaporte = graphene.String(required=False)

    profile = graphene.Field(DriverProfileType)

    @staticmethod
    def mutate(
        root,
        info,
        licencia_numero: Optional[str] = None,
        vehiculo_tipo: Optional[str] = None,
        vehiculo_placa: Optional[str] = None,
        vehiculo_color: Optional[str] = None,
        capacidad_paquetes: Optional[int] = None,
        telefono: Optional[str] = None,
        cedula_pasaporte: Optional[str] = None,
    ):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Autenticación requerida")

        if capacidad_paquetes is not None and capacidad_paquetes <= 0:
            raise GraphQLError("La capacidad debe ser mayor a cero.")
        if capacidad_paquetes is not None and capacidad_paquetes > 50:
            raise GraphQLError(
                "La capacidad máxima permitida es 50 paquetes o pasajeros."
            )
        if vehiculo_color is not None and len(vehiculo_color.strip()) > 30:
            raise GraphQLError(
                "El color del vehículo no puede superar los 30 caracteres."
            )
        if vehiculo_placa is not None and len(vehiculo_placa.strip()) > 20:
            raise GraphQLError(
                "La placa del vehículo no puede superar los 20 caracteres."
            )

        user_fields_to_update = []
        if telefono is not None and telefono.strip():
            user.telefono = telefono.strip()
            user_fields_to_update.append("telefono")
        if cedula_pasaporte is not None and cedula_pasaporte.strip():
            cedula_clean = cedula_pasaporte.strip()
            if (
                Usuario.objects
                .filter(cedula_pasaporte=cedula_clean)
                .exclude(pk=user.pk)
                .exists()
            ):
                raise GraphQLError("Esa cédula ya está registrada")
            user.cedula_pasaporte = cedula_clean
            user_fields_to_update.append("cedula_pasaporte")

        profile_defaults = {
            "licencia_numero": licencia_numero,
            "vehiculo_tipo": vehiculo_tipo,
            "vehiculo_placa": vehiculo_placa,
            "vehiculo_color": vehiculo_color,
            "capacidad_paquetes": capacidad_paquetes or 1,
        }
        profile, _ = DriverProfile.objects.update_or_create(
            usuario=user,
            defaults=profile_defaults,
        )
        if not user.es_conductor:
            user.es_conductor = True
            user_fields_to_update.append("es_conductor")
        if user_fields_to_update:
            user.save(update_fields=user_fields_to_update)

        return RegisterDriver(profile=profile)


class SetDriverStatus(graphene.Mutation):
    class Arguments:
        estado = graphene.Argument(DriverStatusEnum, required=True)
        ubicacion_lat = graphene.Float(required=False)
        ubicacion_lng = graphene.Float(required=False)

    profile = graphene.Field(DriverProfileType)

    @staticmethod
    def mutate(root, info, estado: DriverStatusEnum, ubicacion_lat: Optional[float] = None, ubicacion_lng: Optional[float] = None):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Autenticación requerida")

        try:
            profile = user.perfil_conductor
        except DriverProfile.DoesNotExist as exc:
            raise GraphQLError("El usuario no tiene perfil de conductor") from exc

        normalized_estado = estado.value if hasattr(estado, "value") else str(estado).lower()
        allowed = {choice[0] for choice in DriverProfile.ESTADOS}
        if normalized_estado not in allowed:
            raise GraphQLError("Estado de conductor inválido")

        if (
            normalized_estado != DriverProfile.ESTADO_OFFLINE
            and not profile.is_complete
        ):
            raise GraphQLError(
                "Completa tu perfil de conductor (datos, vehículo y fotos de "
                "tus documentos) antes de activarte."
            )

        profile.estado = normalized_estado
        if ubicacion_lat is not None:
            profile.ubicacion_lat = Decimal(str(ubicacion_lat))
        if ubicacion_lng is not None:
            profile.ubicacion_lng = Decimal(str(ubicacion_lng))
        profile.save(update_fields=["estado", "ubicacion_lat", "ubicacion_lng", "actualizado"])
        return SetDriverStatus(profile=profile)


class UpdateTiendaUbicacion(graphene.Mutation):
    class Arguments:
        lat = graphene.Float(required=True)
        lng = graphene.Float(required=True)

    tienda = graphene.Field("store.graphql.types.TiendaType")

    @staticmethod
    def mutate(root, info, lat: float, lng: float):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Autenticación requerida")
        if getattr(user, "rol", None) != Usuario.ES_TIENDA:
            raise GraphQLError("Solo las tiendas pueden actualizar su ubicación")

        if not (-90.0 <= lat <= 90.0):
            raise GraphQLError("lat fuera de rango")
        if not (-180.0 <= lng <= 180.0):
            raise GraphQLError("lng fuera de rango")

        try:
            tienda = Tienda.objects.get(usuario=user)
        except Tienda.DoesNotExist as exc:
            raise GraphQLError("La tienda del usuario no existe") from exc

        tienda.ubicacion_lat = Decimal(str(lat))
        tienda.ubicacion_lng = Decimal(str(lng))
        tienda.ubicacion_actualizada = timezone.now()
        tienda.save(
            update_fields=["ubicacion_lat", "ubicacion_lng", "ubicacion_actualizada"]
        )
        return UpdateTiendaUbicacion(tienda=tienda)


class CreateServiceRequest(graphene.Mutation):
    class Arguments:
        tipo = graphene.Argument(ServiceRequestTypeEnum, required=True)
        store_order_id = graphene.ID(required=False)
        pickup_direccion = graphene.String(required=False)
        pickup_lat = graphene.Float(required=False)
        pickup_lng = graphene.Float(required=False)
        dropoff_direccion = graphene.String(required=False)
        dropoff_lat = graphene.Float(required=False)
        dropoff_lng = graphene.Float(required=False)
        notas = graphene.String(required=False)
        costo_estimado = graphene.Float(
            required=False,
            description="Obsoleto: el costo lo calcula el servidor según la tarifa vigente.",
        )

    service_request = graphene.Field(ServiceRequestType)

    @staticmethod
    def mutate(
        root,
        info,
        tipo: ServiceRequestTypeEnum,
        store_order_id: Optional[int] = None,
        pickup_direccion: Optional[str] = None,
        pickup_lat: Optional[float] = None,
        pickup_lng: Optional[float] = None,
        dropoff_direccion: Optional[str] = None,
        dropoff_lat: Optional[float] = None,
        dropoff_lng: Optional[float] = None,
        notas: Optional[str] = None,
        costo_estimado: Optional[float] = None,
    ):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Autenticación requerida")

        tipo_value = tipo.value if hasattr(tipo, "value") else str(tipo)

        store_order = None
        if store_order_id is not None:
            try:
                store_order = StoreOrder.objects.select_related(
                    "usuario", "producto__tienda__usuario"
                ).get(
                    Q(usuario=user) | Q(producto__tienda__usuario=user),
                    pk=store_order_id,
                )
            except StoreOrder.DoesNotExist as exc:
                raise GraphQLError("No se encontró la orden asociada para delivery") from exc
            if store_order.service_requests.exclude(
                estado=ServiceRequest.ESTADO_CANCELADO
            ).exists():
                raise GraphQLError("Esta orden ya tiene un delivery en curso")

        servicio = ServiceRequest(
            tipo=tipo_value,
            cliente=user,
            store_order=store_order,
            pickup_direccion=pickup_direccion,
            dropoff_direccion=dropoff_direccion,
            notas=notas,
        )

        if pickup_lat is not None:
            servicio.pickup_lat = Decimal(str(pickup_lat))
        if pickup_lng is not None:
            servicio.pickup_lng = Decimal(str(pickup_lng))
        if dropoff_lat is not None:
            servicio.dropoff_lat = Decimal(str(dropoff_lat))
        if dropoff_lng is not None:
            servicio.dropoff_lng = Decimal(str(dropoff_lng))

        # Best-effort: calcular ruta usando Mapbox si tenemos coordenadas.
        has_coordinates = (
            servicio.pickup_lat is not None
            and servicio.pickup_lng is not None
            and servicio.dropoff_lat is not None
            and servicio.dropoff_lng is not None
        )
        if has_coordinates:
            try:
                data = fetch_directions(
                    (float(servicio.pickup_lng), float(servicio.pickup_lat)),
                    (float(servicio.dropoff_lng), float(servicio.dropoff_lat)),
                )
                summary = extract_route_summary(data)
                if summary:
                    servicio.distancia_metros = summary.get("distance_m")
                    servicio.duracion_segundos = summary.get("duration_s")
                    servicio.ruta_geojson = summary.get("geometry")
            except MapboxConfigurationError:
                # No token configurado, guardamos sin ruta
                pass
            except Exception:
                # No interrumpir la creación ante errores de red u otros.
                pass
            if servicio.distancia_metros is None:
                servicio.distancia_metros = haversine_metros(
                    float(servicio.pickup_lat),
                    float(servicio.pickup_lng),
                    float(servicio.dropoff_lat),
                    float(servicio.dropoff_lng),
                )

        if (
            tipo_value == ServiceRequest.TIPO_DELIVERY
            and servicio.distancia_metros is not None
        ):
            servicio.costo_estimado = calcular_costo_delivery(servicio.distancia_metros)

        servicio.save()

        if store_order and store_order.usuario_id != user.id:
            Notificacion.objects.create(
                usuario=store_order.usuario,
                titulo="Delivery solicitado",
                mensaje=(
                    f"La tienda solicitó un delivery para tu orden #{store_order.id}. "
                    "Podrás seguirlo desde tu orden."
                ),
                tipo=Notificacion.TIPO_SERVICIO,
                data={"service_id": servicio.id},
            )

        return CreateServiceRequest(service_request=servicio)


class AssignServiceRequest(graphene.Mutation):
    class Arguments:
        service_request_id = graphene.ID(required=True)

    service_request = graphene.Field(ServiceRequestType)

    @staticmethod
    def mutate(root, info, service_request_id: int):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Autenticación requerida")
        if not getattr(user, "es_conductor", False):
            raise GraphQLError("Solo los conductores pueden tomar solicitudes")

        try:
            servicio = ServiceRequest.objects.get(pk=service_request_id)
        except ServiceRequest.DoesNotExist as exc:
            raise GraphQLError("Solicitud no encontrada") from exc

        if servicio.estado != ServiceRequest.ESTADO_PENDIENTE or servicio.driver_id:
            raise GraphQLError("La solicitud ya no está disponible para postulaciones")

        if servicio.cliente_id == user.id:
            raise GraphQLError("No puedes tomar una solicitud creada por ti mismo")

        candidate, created = ServiceRequestCandidate.objects.get_or_create(
            service_request=servicio,
            driver=user,
            defaults={'estado': ServiceRequestCandidate.ESTADO_POSTULADO},
        )
        if not created and candidate.estado != ServiceRequestCandidate.ESTADO_POSTULADO:
            raise GraphQLError("Ya no puedes postularte a esta solicitud")

        Notificacion.objects.create(
            usuario_id=servicio.cliente_id,
            titulo='Nuevo conductor disponible',
            mensaje='Un conductor se postuló. Revisa sus datos y escógelo si te conviene.',
            tipo=Notificacion.TIPO_SERVICIO,
            data={'service_id': servicio.id},
        )

        return AssignServiceRequest(service_request=servicio)


class SelectServiceRequestDriver(graphene.Mutation):
    class Arguments:
        service_request_id = graphene.ID(required=True)
        driver_id = graphene.ID(required=True)

    service_request = graphene.Field(ServiceRequestType)

    @staticmethod
    def mutate(root, info, service_request_id: int, driver_id: int):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError('Autenticación requerida')
        servicio = ServiceRequest.objects.select_related('cliente').filter(
            pk=service_request_id, cliente=user
        ).first()
        if not servicio or servicio.estado != ServiceRequest.ESTADO_PENDIENTE:
            raise GraphQLError('La solicitud ya no está disponible')
        candidate = ServiceRequestCandidate.objects.filter(
            service_request=servicio,
            driver_id=driver_id,
            estado=ServiceRequestCandidate.ESTADO_POSTULADO,
        ).select_related('driver').first()
        if not candidate:
            raise GraphQLError('Ese conductor ya no está disponible')

        with transaction.atomic():
            servicio.marcar_asignado(driver=candidate.driver)
            ServiceRequestCandidate.objects.filter(service_request=servicio).exclude(
                pk=candidate.pk
            ).update(estado=ServiceRequestCandidate.ESTADO_RECHAZADO)
            candidate.estado = ServiceRequestCandidate.ESTADO_SELECCIONADO
            candidate.save(update_fields=['estado', 'actualizado'])

        Conversation.get_or_create_between(servicio.cliente, candidate.driver)
        driver_nombre = candidate.driver.first_name or 'Tu conductor'
        Notificacion.objects.create(
            usuario_id=servicio.cliente_id,
            titulo='Conductor seleccionado',
            mensaje=(
                f'{driver_nombre} fue seleccionado. Verifica el vehículo al recoger '
                'y comparte el código para confirmar el inicio.'
            ),
            tipo=Notificacion.TIPO_SERVICIO,
            data={'service_id': servicio.id},
        )
        Notificacion.objects.create(
            usuario_id=candidate.driver_id,
            titulo='Te seleccionaron para un servicio',
            mensaje='Dirígete al punto de recogida y solicita el código antes de iniciar.',
            tipo=Notificacion.TIPO_SERVICIO,
            data={'service_id': servicio.id},
        )
        return SelectServiceRequestDriver(service_request=servicio)


SERVICE_TRANSICIONES_VALIDAS = {
    ServiceRequest.ESTADO_PENDIENTE: {ServiceRequest.ESTADO_CANCELADO},
    ServiceRequest.ESTADO_ASIGNADO: {
        ServiceRequest.ESTADO_LLEGO_RECOGIDA,
        ServiceRequest.ESTADO_CANCELADO,
    },
    ServiceRequest.ESTADO_LLEGO_RECOGIDA: {
        ServiceRequest.ESTADO_EN_CURSO,
        ServiceRequest.ESTADO_CANCELADO,
    },
    ServiceRequest.ESTADO_EN_CURSO: {ServiceRequest.ESTADO_LLEGO_DESTINO},
    ServiceRequest.ESTADO_LLEGO_DESTINO: {ServiceRequest.ESTADO_COMPLETADO},
}

SERVICE_ESTADOS_SOLO_CONDUCTOR = {
    ServiceRequest.ESTADO_LLEGO_RECOGIDA,
    ServiceRequest.ESTADO_EN_CURSO,
    ServiceRequest.ESTADO_LLEGO_DESTINO,
}


def _notificar_transicion_servicio(servicio: ServiceRequest, estado_value: str):
    receptor = servicio.receptor_codigo
    destinatarios = {servicio.cliente_id, receptor.id}
    if servicio.driver_id:
        destinatarios.add(servicio.driver_id)
    es_taxi = servicio.tipo == ServiceRequest.TIPO_TAXI

    mensajes = {
        ServiceRequest.ESTADO_LLEGO_RECOGIDA: (
            'Tu conductor llegó',
            'El conductor está en el punto de recogida.'
            if es_taxi
            else 'El conductor llegó al punto de recogida del paquete.',
        ),
        ServiceRequest.ESTADO_EN_CURSO: (
            'Viaje en curso' if es_taxi else 'Tu paquete va en camino',
            'El conductor va rumbo al destino.',
        ),
        ServiceRequest.ESTADO_LLEGO_DESTINO: (
            'El conductor llegó al destino',
            'Entrega tu código de confirmación al conductor para finalizar.',
        ),
        ServiceRequest.ESTADO_COMPLETADO: (
            'Servicio completado',
            '¡Viaje finalizado con éxito!' if es_taxi else 'Tu entrega fue confirmada con éxito.',
        ),
    }
    contenido = mensajes.get(estado_value)
    if not contenido:
        return
    titulo, mensaje = contenido
    for usuario_id in destinatarios:
        Notificacion.objects.create(
            usuario_id=usuario_id,
            titulo=titulo,
            mensaje=mensaje,
            tipo=Notificacion.TIPO_SERVICIO,
            data={'service_id': servicio.id, 'estado': estado_value},
        )


class UpdateServiceRequestStatus(graphene.Mutation):
    class Arguments:
        service_request_id = graphene.ID(required=True)
        estado = graphene.Argument(ServiceRequestStatusEnum, required=True)
        codigo_entrega = graphene.String(required=False)

    service_request = graphene.Field(ServiceRequestType)

    @staticmethod
    def mutate(
        root,
        info,
        service_request_id: int,
        estado: ServiceRequestStatusEnum,
        codigo_entrega: Optional[str] = None,
    ):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Autenticación requerida")

        try:
            servicio = ServiceRequest.objects.select_related(
                "driver",
                "cliente",
                "store_order__usuario",
                "store_order__producto__tienda__usuario",
            ).get(pk=service_request_id)
        except ServiceRequest.DoesNotExist as exc:
            raise GraphQLError("Solicitud no encontrada") from exc

        estado_value = estado.value if hasattr(estado, "value") else str(estado).lower()
        allowed = {member.value for member in ServiceRequestStatusEnum}
        if estado_value not in allowed:
            raise GraphQLError("Estado inválido")

        is_driver = servicio.driver_id == getattr(user, "id", None)
        is_client = servicio.cliente_id == getattr(user, "id", None)

        if not (is_driver or is_client):
            raise GraphQLError("No tienes permisos para actualizar esta solicitud")

        transiciones = SERVICE_TRANSICIONES_VALIDAS.get(servicio.estado, set())
        if estado_value not in transiciones:
            raise GraphQLError(
                f"No se puede pasar de '{servicio.estado}' a '{estado_value}'"
            )

        if estado_value == ServiceRequest.ESTADO_CANCELADO and not is_client:
            raise GraphQLError("Solo el cliente puede cancelar la solicitud")

        if estado_value in SERVICE_ESTADOS_SOLO_CONDUCTOR and not is_driver:
            raise GraphQLError("Solo el conductor asignado puede marcar este estado")

        if estado_value == ServiceRequest.ESTADO_EN_CURSO:
            if not codigo_entrega or codigo_entrega.strip() != servicio.codigo_entrega:
                raise GraphQLError(
                    "Código inválido. Verifica el vehículo y pide el código al usuario antes de iniciar."
                )

        servicio.estado = estado_value
        if estado_value == ServiceRequest.ESTADO_COMPLETADO:
            servicio.completado_en = timezone.now()
        elif estado_value == ServiceRequest.ESTADO_CANCELADO:
            servicio.cancelado_en = timezone.now()

        with transaction.atomic():
            servicio.save(
                update_fields=[
                    "estado",
                    "completado_en",
                    "cancelado_en",
                    "actualizado",
                ]
            )

            order = servicio.store_order
            if (
                estado_value == ServiceRequest.ESTADO_COMPLETADO
                and order is not None
                and order.estado == StoreOrder.ESTADO_EN_CURSO
            ):
                # El signal notificar_orden avisa al comprador del cambio de estado.
                order.estado = StoreOrder.ESTADO_COMPLETADO
                order.save(update_fields=["estado", "actualizado"])

                tienda_user_id = (
                    order.producto.tienda.usuario_id
                    if order.producto and order.producto.tienda
                    else None
                )
                if tienda_user_id:
                    Notificacion.objects.create(
                        usuario_id=tienda_user_id,
                        titulo="Orden entregada",
                        mensaje=(
                            f"La orden #{order.id} fue entregada por el conductor "
                            "y se marcó como completada."
                        ),
                        tipo=Notificacion.TIPO_ORDEN,
                        data={"order_id": order.id, "view": "store"},
                    )

        _notificar_transicion_servicio(servicio, estado_value)

        return UpdateServiceRequestStatus(service_request=servicio)


class GoogleLogin(graphene.Mutation):
    class Arguments:
        id_token = graphene.String(required=True)

    access_token = graphene.String()
    refresh_token = graphene.String()
    user = graphene.Field(UsuarioType)
    is_new_user = graphene.Boolean()
    requires_role_selection = graphene.Boolean()

    @staticmethod
    def mutate(root, info, id_token: str):
        try:
            from google.oauth2 import id_token as google_id_token
            from google.auth.transport import requests as google_requests
        except ImportError as exc:
            raise GraphQLError(
                "google-auth no está instalado en el backend"
            ) from exc

        client_id = getattr(settings, "GOOGLE_WEB_CLIENT_ID", "")
        if not client_id:
            raise GraphQLError("GOOGLE_WEB_CLIENT_ID no configurado en el backend")

        try:
            id_info = google_id_token.verify_oauth2_token(
                id_token, google_requests.Request(), client_id
            )
        except ValueError as exc:
            raise GraphQLError(f"Token de Google inválido: {exc}") from exc

        email = (id_info.get("email") or "").strip().lower()
        if not email:
            raise GraphQLError("El token de Google no contiene email")
        if not id_info.get("email_verified", False):
            raise GraphQLError("El email de Google no está verificado")

        first_name = id_info.get("given_name") or ""
        last_name = id_info.get("family_name") or ""

        try:
            user = Usuario.objects.get(email=email)
            is_new_user = False
        except Usuario.DoesNotExist:
            username_base = email.split("@")[0][:140] or "usuario"
            username = username_base
            suffix = 0
            while Usuario.objects.filter(username=username).exists():
                suffix += 1
                username = f"{username_base}{suffix}"[:150]
            user = Usuario.objects.create_user(
                username=username,
                email=email,
                password=get_random_string(32),
                first_name=first_name,
                last_name=last_name,
                registro_completo=False,
            )
            is_new_user = True

        if not user.is_active:
            raise GraphQLError("La cuenta está inactiva")

        refresh = RefreshToken.for_user(user)
        return GoogleLogin(
            access_token=str(refresh.access_token),
            refresh_token=str(refresh),
            user=user,
            is_new_user=is_new_user,
            requires_role_selection=not user.registro_completo,
        )


class UpdateMyRole(graphene.Mutation):
    class Arguments:
        rol = graphene.Argument(UsuarioRolEnum, required=True)

    user = graphene.Field(UsuarioType)

    @staticmethod
    def mutate(root, info, rol):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Autenticación requerida")

        rol_value = rol.value if hasattr(rol, "value") else rol
        valid_roles = {choice for choice, _ in Usuario.ROLES}
        if rol_value not in valid_roles:
            raise GraphQLError("Rol inválido")

        user.rol = rol_value
        user.save(update_fields=["rol"])
        return UpdateMyRole(user=user)


class CompleteMyProfile(graphene.Mutation):
    """Completa el registro de un usuario creado vía Google (rol + datos requeridos)."""

    class Arguments:
        rol = graphene.Argument(UsuarioRolEnum, required=True)
        telefono = graphene.String(required=True)
        first_name = graphene.String()
        last_name = graphene.String()
        cedula_pasaporte = graphene.String()
        edad = graphene.Int()
        genero = graphene.String()
        ingresos_minimos_mensuales = graphene.Float()
        nombre_tienda = graphene.String()
        direccion_tienda = graphene.String()
        telefono_tienda = graphene.String()
        informacion_fiscal = graphene.String()
        ubicacion_lat = graphene.Float()
        ubicacion_lng = graphene.Float()

    user = graphene.Field(UsuarioType)

    @staticmethod
    def mutate(
        root,
        info,
        rol,
        telefono: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        cedula_pasaporte: Optional[str] = None,
        edad: Optional[int] = None,
        genero: Optional[str] = None,
        ingresos_minimos_mensuales: Optional[float] = None,
        nombre_tienda: Optional[str] = None,
        direccion_tienda: Optional[str] = None,
        telefono_tienda: Optional[str] = None,
        informacion_fiscal: Optional[str] = None,
        ubicacion_lat: Optional[float] = None,
        ubicacion_lng: Optional[float] = None,
    ):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Autenticación requerida")

        rol_value = rol.value if hasattr(rol, "value") else rol
        valid_roles = {choice for choice, _ in Usuario.ROLES}
        if rol_value not in valid_roles:
            raise GraphQLError("Rol inválido")

        telefono = (telefono or "").strip()
        cedula = (cedula_pasaporte or "").strip()
        nombre_tienda = (nombre_tienda or "").strip()
        direccion_tienda = (direccion_tienda or "").strip()

        if not telefono:
            raise GraphQLError("El teléfono es requerido")
        if rol_value in (Usuario.ES_TIENDA, Usuario.ES_CONDUCTOR) and not cedula:
            raise GraphQLError("La cédula o pasaporte es requerida para este rol")
        if rol_value == Usuario.ES_TIENDA:
            if not nombre_tienda:
                raise GraphQLError("El nombre de la tienda es requerido")
            if not direccion_tienda:
                raise GraphQLError("La dirección de la tienda es requerida")

        if cedula and Usuario.objects.filter(
            cedula_pasaporte=cedula
        ).exclude(pk=user.pk).exists():
            raise GraphQLError("La cédula o pasaporte ya está registrada")

        if genero:
            genero = genero.strip().upper()
            valid_generos = {choice for choice, _ in Usuario.GENEROS}
            if genero not in valid_generos:
                raise GraphQLError("Género inválido")

        user.rol = rol_value
        user.telefono = telefono
        if first_name and first_name.strip():
            user.first_name = first_name.strip()
        if last_name and last_name.strip():
            user.last_name = last_name.strip()
        if cedula:
            user.cedula_pasaporte = cedula
        if edad is not None:
            user.edad = edad
        if genero:
            user.genero = genero
        if ingresos_minimos_mensuales is not None:
            try:
                user.ingresos_minimos_mensuales = Decimal(
                    str(ingresos_minimos_mensuales)
                )
            except InvalidOperation as exc:
                raise GraphQLError("Ingresos mínimos inválidos") from exc
        user.registro_completo = True
        user.save()

        if rol_value == Usuario.ES_TIENDA:
            tienda, _created = Tienda.objects.get_or_create(
                usuario=user,
                defaults={
                    "nombre": nombre_tienda,
                    "direccion": direccion_tienda,
                    "telefono": (telefono_tienda or "").strip() or telefono,
                    "informacion_fiscal": (informacion_fiscal or "").strip() or None,
                },
            )
            if ubicacion_lat is not None and ubicacion_lng is not None:
                tienda.ubicacion_lat = Decimal(str(ubicacion_lat))
                tienda.ubicacion_lng = Decimal(str(ubicacion_lng))
                tienda.ubicacion_actualizada = timezone.now()
                tienda.save(
                    update_fields=[
                        "ubicacion_lat",
                        "ubicacion_lng",
                        "ubicacion_actualizada",
                    ]
                )

        return CompleteMyProfile(user=user)


class DeleteMyAccount(graphene.Mutation):
    """Desactiva la cuenta del usuario autenticado (soft delete)."""

    class Arguments:
        password = graphene.String()

    ok = graphene.Boolean()

    @staticmethod
    def mutate(root, info, password: Optional[str] = None):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Autenticación requerida")

        # La confirmación principal es el modal en la app; si el cliente envía
        # contraseña la verificamos como capa extra (cuentas Google no la conocen).
        if password and not user.check_password(password):
            raise GraphQLError("Contraseña incorrecta")

        user.is_active = False
        user.save(update_fields=["is_active"])
        return DeleteMyAccount(ok=True)


class RequestPasswordReset(graphene.Mutation):
    """Envía un código OTP de 6 dígitos al correo para recuperar la contraseña."""

    class Arguments:
        email = graphene.String(required=True)

    ok = graphene.Boolean()

    @staticmethod
    def mutate(root, info, email: str):
        email = (email or "").strip().lower()
        if not email:
            raise GraphQLError("El correo es requerido")

        user = Usuario.objects.filter(email=email, is_active=True).first()
        # Respondemos ok aunque el correo no exista para no revelar
        # qué cuentas están registradas.
        if user:
            codigo = get_random_string(6, "0123456789")
            PasswordResetCode.objects.create(usuario=user, codigo=codigo)
            try:
                send_app_email(
                    subject="TuPlaza – Código para recuperar tu contraseña",
                    message=(
                        f"Hola {user.first_name or ''}\n\n"
                        f"Tu código de recuperación es: {codigo}\n\n"
                        f"Vence en {PasswordResetCode.VALIDEZ_MINUTOS} minutos. "
                        "Si no solicitaste este código, ignora este correo."
                    ),
                    recipient=user.email,
                )
            except Exception as exc:
                # Incluimos la causa para poder diagnosticar desde la app,
                # ya que los logs de Railway no siempre están a mano.
                causa = exc.__cause__ or exc
                raise GraphQLError(
                    f"No pudimos enviar el correo. Detalle: {causa}"
                ) from exc
        return RequestPasswordReset(ok=True)


class ResetPassword(graphene.Mutation):
    """Cambia la contraseña usando el código OTP enviado por correo."""

    class Arguments:
        email = graphene.String(required=True)
        codigo = graphene.String(required=True)
        new_password = graphene.String(required=True)

    ok = graphene.Boolean()

    @staticmethod
    def mutate(root, info, email: str, codigo: str, new_password: str):
        email = (email or "").strip().lower()
        codigo = (codigo or "").strip()
        if len(new_password or "") < 8:
            raise GraphQLError("La contraseña debe tener al menos 8 caracteres")
        try:
            validate_password(new_password, user)
        except Exception as exc:
            raise GraphQLError(str(exc)) from exc

        user = Usuario.objects.filter(email=email, is_active=True).first()
        reset_code = (
            PasswordResetCode.objects.filter(usuario=user, usado=False).first()
            if user
            else None
        )
        if not reset_code or not reset_code.esta_vigente():
            raise GraphQLError("Código inválido o vencido. Solicita uno nuevo.")

        if reset_code.codigo != codigo:
            reset_code.intentos += 1
            reset_code.save(update_fields=["intentos"])
            raise GraphQLError("Código incorrecto.")

        user.set_password(new_password)
        user.save(update_fields=["password"])
        reset_code.usado = True
        reset_code.save(update_fields=["usado"])

        # La contraseña ya cambió; si este aviso falla no rompemos el flujo.
        try:
            send_app_email(
                subject="TuPlaza – Tu contraseña fue cambiada",
                message=(
                    f"Hola {user.first_name or ''}\n\n"
                    "Tu contraseña se cambió correctamente. Ya puedes iniciar "
                    "sesión con tu nueva contraseña.\n\n"
                    "Si no fuiste tú, solicita de inmediato un nuevo código "
                    "de recuperación desde la app para proteger tu cuenta."
                ),
                recipient=user.email,
            )
        except Exception:
            logger.warning(
                "No se pudo enviar el aviso de cambio de contraseña a %s",
                user.email,
            )
        return ResetPassword(ok=True)


class ChangePassword(graphene.Mutation):
    """Cambia la contraseña de un usuario autenticado, verificando la actual."""

    class Arguments:
        current_password = graphene.String(required=True)
        new_password = graphene.String(required=True)

    ok = graphene.Boolean()

    @staticmethod
    def mutate(root, info, current_password: str, new_password: str):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Autenticación requerida")

        if len(new_password or "") < 8:
            raise GraphQLError("La nueva contraseña debe tener al menos 8 caracteres")
        try:
            validate_password(new_password, user)
        except Exception as exc:
            raise GraphQLError(str(exc)) from exc

        if not user.check_password(current_password or ""):
            raise GraphQLError("La contraseña actual es incorrecta")

        user.set_password(new_password)
        user.save(update_fields=["password"])

        try:
            send_app_email(
                subject="TuPlaza – Tu contraseña fue cambiada",
                message=(
                    f"Hola {user.first_name or ''}\n\n"
                    "Tu contraseña se cambió correctamente desde tu perfil.\n\n"
                    "Si no fuiste tú, solicita de inmediato un nuevo código "
                    "de recuperación desde la app para proteger tu cuenta."
                ),
                recipient=user.email,
            )
        except Exception:
            logger.warning(
                "No se pudo enviar el aviso de cambio de contraseña a %s",
                user.email,
            )
        return ChangePassword(ok=True)


class Mutation(graphene.ObjectType):
    login = Login.Field()
    google_login = GoogleLogin.Field()
    update_my_role = UpdateMyRole.Field()
    complete_my_profile = CompleteMyProfile.Field()
    request_password_reset = RequestPasswordReset.Field()
    reset_password = ResetPassword.Field()
    change_password = ChangePassword.Field()
    delete_my_account = DeleteMyAccount.Field()
    create_store_order = CreateStoreOrder.Field()
    checkout_cart = CheckoutCart.Field()
    update_store_order_status = UpdateStoreOrderStatus.Field()
    create_store_order_review = CreateStoreOrderReview.Field()
    create_store_order_seller_review = CreateStoreOrderSellerReview.Field()
    register_driver = RegisterDriver.Field()
    set_driver_status = SetDriverStatus.Field()
    update_tienda_ubicacion = UpdateTiendaUbicacion.Field()
    create_service_request = CreateServiceRequest.Field()
    assign_service_request = AssignServiceRequest.Field()
    select_service_request_driver = SelectServiceRequestDriver.Field()
    update_service_request_status = UpdateServiceRequestStatus.Field()
