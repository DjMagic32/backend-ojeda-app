import graphene
from django.db.models import Avg
from graphene_django import DjangoObjectType

from store.models import (
    DriverProfile,
    ProductoTienda,
    ServiceRequest,
    StoreOrder,
    StoreOrderReview,
    StoreOrderSellerReview,
    Tienda,
    Usuario,
    Categoria,
)


def _absolute_uri(info, file_field):
    if not file_field:
        return None
    request = getattr(info, "context", None)
    url = getattr(file_field, "url", None)
    if not url:
        return None
    if request and hasattr(request, "build_absolute_uri"):
        try:
            return request.build_absolute_uri(url)
        except Exception:  # pragma: no cover - fallback for malformed request
            return url
    return url


class TiendaType(DjangoObjectType):
    usuario = graphene.Int()
    logo = graphene.String()

    class Meta:
        model = Tienda
        fields = (
            "id",
            "usuario",
            "nombre",
            "direccion",
            "telefono",
            "logo",
            "informacion_fiscal",
            "ubicacion_lat",
            "ubicacion_lng",
            "ubicacion_actualizada",
            "creado",
        )

    def resolve_usuario(self, info):  # noqa: D401 - simple id mapping
        return self.usuario_id

    def resolve_logo(self, info):
        return _absolute_uri(info, self.logo)


class CategoriaType(DjangoObjectType):
    thumbnail = graphene.String()

    class Meta:
        model = Categoria
        fields = (
            "id",
            "nombre",
            "descripcion",
            "tipo",
            "thumbnail",
        )

    def resolve_thumbnail(self, info):
        return _absolute_uri(info, self.thumbnail)


class ProductoTiendaType(DjangoObjectType):
    tienda = graphene.Int()
    imagen = graphene.String()
    reviews = graphene.List(lambda: StoreOrderReviewType)
    average_rating = graphene.Float()
    total_reviews = graphene.Int()
    categoria = graphene.Field(CategoriaType)

    class Meta:
        model = ProductoTienda
        fields = (
            "id",
            "tienda",
            "nombre",
            "descripcion",
            "precio",
            "moneda",
            "stock",
            "tipo",
            "imagen",
            "categoria",
        )

    def resolve_tienda(self, info):
        return self.tienda_id

    def resolve_imagen(self, info):
        return _absolute_uri(info, self.imagen)

    def resolve_reviews(self, info):
        return list(
            self.reviews.select_related('usuario').all()
        )

    def resolve_average_rating(self, info):
        aggregate = self.reviews.aggregate(avg=Avg('rating'))
        average = aggregate.get('avg')
        return float(average) if average is not None else None

    def resolve_total_reviews(self, info):
        return self.reviews.count()

    def resolve_categoria(self, info):
        return self.categoria


class StoreOrderReviewType(DjangoObjectType):
    order = graphene.Int()
    usuario = graphene.Int()
    usuario_detalle = graphene.Field(lambda: UsuarioType)
    producto = graphene.Field(lambda: ProductoTiendaType)

    class Meta:
        model = StoreOrderReview
        fields = (
            'id',
            'order',
            'producto',
            'usuario',
            'rating',
            'comentario',
            'creado',
            'actualizado',
        )

    def resolve_order(self, info):
        return self.order_id

    def resolve_usuario(self, info):
        return self.usuario_id

    def resolve_usuario_detalle(self, info):
        return self.usuario

    def resolve_producto(self, info):
        return self.producto


class UsuarioType(DjangoObjectType):
    tienda = graphene.Field(TiendaType)
    foto_identificacion = graphene.String()
    groups = graphene.List(graphene.Int)
    user_permissions = graphene.List(graphene.Int)
    perfil_conductor = graphene.Field(lambda: DriverProfileType)

    class Meta:
        model = Usuario
        fields = (
            "id",
            "last_login",
            "is_superuser",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_staff",
            "is_active",
            "date_joined",
            "rol",
            "edad",
            "genero",
            "telefono",
            "cedula_pasaporte",
            "foto_identificacion",
            "ingresos_minimos_mensuales",
            "es_conductor",
            "groups",
            "user_permissions",
        )

    def resolve_tienda(self, info):
        try:
            return self.tienda
        except Tienda.DoesNotExist:
            return None

    def resolve_foto_identificacion(self, info):
        return _absolute_uri(info, self.foto_identificacion)

    def resolve_groups(self, info):
        return list(self.groups.values_list("id", flat=True))

    def resolve_user_permissions(self, info):
        return list(self.user_permissions.values_list("id", flat=True))

    def resolve_perfil_conductor(self, info):
        try:
            return self.perfil_conductor
        except DriverProfile.DoesNotExist:
            return None


class StoreOrderType(DjangoObjectType):
    usuario = graphene.Int()
    producto = graphene.Field(ProductoTiendaType)
    review = graphene.Field(StoreOrderReviewType)
    seller_review = graphene.Field(lambda: StoreOrderSellerReviewType)

    class Meta:
        model = StoreOrder
        fields = (
            "id",
            "usuario",
            "producto",
            "cantidad",
            "precio_unitario",
            "total",
            "moneda",
            "tasa_aplicada",
            "estado",
            "direccion_entrega",
            "notas",
            "creado",
            "actualizado",
            "seller_review",
        )

    def resolve_usuario(self, info):
        return self.usuario_id

    def resolve_producto(self, info):
        return self.producto

    def resolve_review(self, info):
        try:
            return self.review
        except StoreOrderReview.DoesNotExist:
            return None

    def resolve_seller_review(self, info):
        try:
            return self.seller_review
        except StoreOrderSellerReview.DoesNotExist:
            return None


class StoreOrderSellerReviewType(DjangoObjectType):
    order = graphene.Int()
    tienda = graphene.Int()
    comprador = graphene.Int()
    tienda_detalle = graphene.Field(lambda: TiendaType)
    comprador_detalle = graphene.Field(lambda: UsuarioType)

    class Meta:
        model = StoreOrderSellerReview
        fields = (
            'id',
            'order',
            'tienda',
            'comprador',
            'rating',
            'comentario',
            'creado',
            'actualizado',
        )

    def resolve_order(self, info):
        return self.order_id

    def resolve_tienda(self, info):
        return self.tienda_id

    def resolve_comprador(self, info):
        return self.comprador_id

    def resolve_tienda_detalle(self, info):
        return self.tienda

    def resolve_comprador_detalle(self, info):
        return self.comprador


class DriverProfileType(DjangoObjectType):
    usuario = graphene.Int()
    is_complete = graphene.Boolean()

    class Meta:
        model = DriverProfile
        fields = (
            "id",
            "usuario",
            "licencia_numero",
            "vehiculo_tipo",
            "vehiculo_placa",
            "vehiculo_color",
            "capacidad_paquetes",
            "estado",
            "ubicacion_lat",
            "ubicacion_lng",
            "actualizado",
        )

    def resolve_usuario(self, info):
        return self.usuario_id

    def resolve_is_complete(self, info):
        return self.is_complete


class ServiceRequestType(DjangoObjectType):
    cliente = graphene.Int()
    driver = graphene.Int()
    store_order = graphene.Field(StoreOrderType)
    ruta_geojson = graphene.JSONString()
    cliente_detalle = graphene.Field(UsuarioType)
    driver_detalle = graphene.Field(UsuarioType)

    class Meta:
        model = ServiceRequest
        fields = (
            "id",
            "tipo",
            "cliente",
            "driver",
            "store_order",
            "pickup_direccion",
            "pickup_lat",
            "pickup_lng",
            "dropoff_direccion",
            "dropoff_lat",
            "dropoff_lng",
            "estado",
            "distancia_metros",
            "duracion_segundos",
            "costo_estimado",
            "ruta_geojson",
            "notas",
            "asignado_en",
            "completado_en",
            "creado",
            "actualizado",
        )

    def resolve_cliente(self, info):
        return self.cliente_id

    def resolve_driver(self, info):
        return self.driver_id if self.driver_id else None

    def resolve_store_order(self, info):
        return self.store_order

    def resolve_ruta_geojson(self, info):
        return self.ruta_geojson

    def resolve_cliente_detalle(self, info):
        return self.cliente

    def resolve_driver_detalle(self, info):
        return self.driver
