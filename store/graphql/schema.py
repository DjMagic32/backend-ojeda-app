from decimal import Decimal
from typing import Iterable, Optional, Type

import graphene
from graphene import Enum
from graphql import GraphQLError
from django.contrib.auth import authenticate
from django.db.models import QuerySet
from rest_framework_simplejwt.tokens import RefreshToken

from store.models import (
    ProductoTienda,
    StoreOrder,
    StoreOrderReview,
    StoreOrderSellerReview,
    Tienda,
    Usuario,
)
from .types import (
    ProductoTiendaType,
    StoreOrderReviewType,
    StoreOrderSellerReviewType,
    StoreOrderType,
    UsuarioType,
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


class Mutation(graphene.ObjectType):
    login = Login.Field()
    create_store_order = CreateStoreOrder.Field()
    update_store_order_status = UpdateStoreOrderStatus.Field()
    create_store_order_review = CreateStoreOrderReview.Field()
    create_store_order_seller_review = CreateStoreOrderSellerReview.Field()
