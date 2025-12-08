from decimal import Decimal
from typing import Iterable, Optional, Type

import graphene
from graphene import Enum
from graphql import GraphQLError
from django.contrib.auth import authenticate
from django.db.models import QuerySet
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from store.models import (
    DriverProfile,
    ProductoTienda,
    ServiceRequest,
    StoreOrder,
    StoreOrderReview,
    StoreOrderSellerReview,
    Tienda,
    Usuario,
)
from .types import (
    DriverProfileType,
    ProductoTiendaType,
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


class ProductScopeEnum(Enum):
    ALL = "all"
    MINE = "mine"


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
    IN_PROGRESS = ServiceRequest.ESTADO_EN_CURSO
    COMPLETED = ServiceRequest.ESTADO_COMPLETADO
    CANCELLED = ServiceRequest.ESTADO_CANCELADO


class DriverStatusEnum(Enum):
    OFFLINE = DriverProfile.ESTADO_OFFLINE
    AVAILABLE = DriverProfile.ESTADO_DISPONIBLE
    ON_TRIP = DriverProfile.ESTADO_EN_VIAJE


class ServiceRequestScopeEnum(Enum):
    CLIENT = "client"
    DRIVER = "driver"


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

    def resolve_me(self, info):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Autenticación requerida")
        return user

    def resolve_store_products(self, info, scope=ProductScopeEnum.ALL):
        scope_value = _normalize_scope(scope, ProductScopeEnum, ProductScopeEnum.ALL.value)
        queryset: QuerySet[ProductoTienda] = ProductoTienda.objects.select_related(
            "tienda",
            "tienda__usuario",
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
                driver_qs = driver_qs | base_queryset.filter(
                    driver__isnull=True,
                    estado=ServiceRequest.ESTADO_PENDIENTE,
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

        if servicio.cliente_id != user.id and servicio.driver_id != user.id:
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

        precio_unitario: Decimal = producto.precio
        total = precio_unitario * Decimal(cantidad)

        order = StoreOrder.objects.create(
            usuario=user,
            producto=producto,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            total=total,
            estado=StoreOrder.ESTADO_PENDIENTE,
            direccion_entrega=direccion_entrega,
            notas=notas,
        )

        return CreateStoreOrder(order=order)


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
    ):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Autenticación requerida")

        if capacidad_paquetes is not None and capacidad_paquetes <= 0:
            raise GraphQLError("La capacidad de paquetes debe ser mayor a cero")

        profile_defaults = {
            "licencia_numero": licencia_numero,
            "vehiculo_tipo": vehiculo_tipo,
            "vehiculo_placa": vehiculo_placa,
            "vehiculo_color": vehiculo_color,
            "capacidad_paquetes": capacidad_paquetes or 1,
            "estado": DriverProfile.ESTADO_DISPONIBLE,
        }
        profile, _ = DriverProfile.objects.update_or_create(
            usuario=user,
            defaults=profile_defaults,
        )
        if not user.es_conductor:
            user.es_conductor = True
            user.save(update_fields=["es_conductor"])

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

        profile.estado = normalized_estado
        if ubicacion_lat is not None:
            profile.ubicacion_lat = Decimal(str(ubicacion_lat))
        if ubicacion_lng is not None:
            profile.ubicacion_lng = Decimal(str(ubicacion_lng))
        profile.save(update_fields=["estado", "ubicacion_lat", "ubicacion_lng", "actualizado"])
        return SetDriverStatus(profile=profile)


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
        costo_estimado = graphene.Float(required=False)

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
                store_order = StoreOrder.objects.select_related("usuario").get(pk=store_order_id, usuario=user)
            except StoreOrder.DoesNotExist as exc:
                raise GraphQLError("No se encontró la orden asociada para delivery") from exc

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

        if costo_estimado is not None:
            servicio.costo_estimado = Decimal(str(costo_estimado))

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

        servicio.save()
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
            raise GraphQLError("La solicitud ya fue tomada o no está disponible")

        servicio.marcar_asignado(driver=user)
        return AssignServiceRequest(service_request=servicio)


class UpdateServiceRequestStatus(graphene.Mutation):
    class Arguments:
        service_request_id = graphene.ID(required=True)
        estado = graphene.Argument(ServiceRequestStatusEnum, required=True)

    service_request = graphene.Field(ServiceRequestType)

    @staticmethod
    def mutate(root, info, service_request_id: int, estado: ServiceRequestStatusEnum):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise GraphQLError("Autenticación requerida")

        try:
            servicio = ServiceRequest.objects.select_related("driver", "cliente").get(pk=service_request_id)
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

        if estado_value == ServiceRequest.ESTADO_CANCELADO and not is_client:
            raise GraphQLError("Solo el cliente puede cancelar la solicitud")

        servicio.estado = estado_value
        if estado_value == ServiceRequest.ESTADO_COMPLETADO:
            servicio.completado_en = timezone.now()
        servicio.save(update_fields=["estado", "completado_en", "actualizado"])

        return UpdateServiceRequestStatus(service_request=servicio)


class Mutation(graphene.ObjectType):
    login = Login.Field()
    create_store_order = CreateStoreOrder.Field()
    update_store_order_status = UpdateStoreOrderStatus.Field()
    create_store_order_review = CreateStoreOrderReview.Field()
    create_store_order_seller_review = CreateStoreOrderSellerReview.Field()
    register_driver = RegisterDriver.Field()
    set_driver_status = SetDriverStatus.Field()
    create_service_request = CreateServiceRequest.Field()
    assign_service_request = AssignServiceRequest.Field()
    update_service_request_status = UpdateServiceRequestStatus.Field()
