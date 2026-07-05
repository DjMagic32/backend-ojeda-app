from decimal import Decimal
from typing import Any

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from .models import (
    Producto,
    Categoria,
    Conversation,
    ExpoPushToken,
    ItemCarrito,
    Carrito,
    Message,
    Pedido,
    Tienda,
    ProductoTienda,
    Comentario,
    ComentarioProducto,
    Referencia,
    TasaCambio,
    Wallet,
    Usuario,
    StoreOrder,
    ProductoFavorito,
    Notificacion,
)

class UsuarioSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Usuario
        fields = '__all__'

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'

class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = '__all__'

class ProductoTiendaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductoTienda
        fields = '__all__'
        read_only_fields = ['tienda']

class ItemCarritoSerializer(serializers.ModelSerializer):
    subtotal = serializers.ReadOnlyField()
    producto_tienda_detalle = ProductoTiendaSerializer(source='producto_tienda', read_only=True)

    class Meta:
        model = ItemCarrito
        fields = ['id', 'producto_tienda', 'producto_tienda_detalle', 'cantidad', 'subtotal']


class ConversationLastMessageSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    contenido = serializers.CharField()
    autor_id = serializers.IntegerField()
    creado = serializers.DateTimeField()
    leido = serializers.BooleanField()


class CarritoSerializer(serializers.ModelSerializer):
    items = ItemCarritoSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Carrito
        fields = ['id', 'usuario', 'items', 'creado', 'total']

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_total(self, obj: Carrito) -> Decimal:
        return sum(item.subtotal for item in obj.items.all())

class PedidoSerializer(serializers.ModelSerializer):
    items = ItemCarritoSerializer(many=True, read_only=True)

    class Meta:
        model = Pedido
        fields = ['id', 'usuario', 'tienda', 'items', 'total', 'creado', 'pagado']

class TiendaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tienda
        fields = '__all__'

class ComentarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comentario
        fields = '__all__'

class ComentarioProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComentarioProducto
        fields = '__all__'

class ReferenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Referencia
        fields = '__all__'

class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = '__all__'


class RegisterUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    nombre = serializers.CharField(required=False, allow_blank=True)
    apellido = serializers.CharField(required=False, allow_blank=True)
    rol = serializers.ChoiceField(choices=Usuario.ROLES, default=Usuario.ES_CLIENTE)
    telefono = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    genero = serializers.ChoiceField(
        choices=Usuario.GENEROS, required=False, allow_blank=True, allow_null=True
    )
    edad = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=18,
        max_value=100,
        error_messages={
            'min_value': 'Debes ser mayor de 18 años para registrarte.',
            'max_value': 'Ingresa una edad válida.',
            'invalid': 'Ingresa una edad válida (solo números).',
        },
    )
    cedula_pasaporte = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    foto_identificacion = serializers.FileField(
        required=False, allow_null=True, use_url=False
    )
    nombre_tienda = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    direccion = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    telefono_tienda = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    informacion_fiscal = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    ubicacion_lat = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True
    )
    ubicacion_lng = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True
    )
    ingresos_minimos_mensuales = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )


class CarritoItemAddSerializer(serializers.Serializer):
    producto_id = serializers.IntegerField()
    cantidad = serializers.IntegerField(required=False, min_value=1, default=1)


class CarritoItemRemoveSerializer(serializers.Serializer):
    producto_id = serializers.IntegerField()


class CarritoItemUpdateSerializer(serializers.Serializer):
    producto_id = serializers.IntegerField()
    cantidad = serializers.IntegerField(min_value=1)


class WalletActionRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0'),
        required=True,
    )


class UsuarioDetalleRequestSerializer(serializers.Serializer):
    token = serializers.CharField()


class StoreOrderSerializer(serializers.ModelSerializer):
    producto = ProductoTiendaSerializer(read_only=True)
    producto_id = serializers.PrimaryKeyRelatedField(
        source='producto', queryset=ProductoTienda.objects.all(), write_only=True
    )

    class Meta:
        model = StoreOrder
        fields = [
            'id',
            'usuario',
            'producto',
            'producto_id',
            'cantidad',
            'precio_unitario',
            'total',
            'moneda',
            'tasa_aplicada',
            'estado',
            'direccion_entrega',
            'notas',
            'creado',
            'actualizado',
        ]
        read_only_fields = [
            'id',
            'usuario',
            'precio_unitario',
            'total',
            'moneda',
            'tasa_aplicada',
            'estado',
            'creado',
            'actualizado',
        ]


class ProductoFavoritoSerializer(serializers.ModelSerializer):
    producto_detalle = ProductoTiendaSerializer(source='producto', read_only=True)

    class Meta:
        model = ProductoFavorito
        fields = ['id', 'producto', 'producto_detalle', 'creado']
        read_only_fields = ['id', 'creado']


class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = ['id', 'titulo', 'mensaje', 'tipo', 'data', 'leido', 'creado']
        read_only_fields = ['id', 'creado']


class ChatParticipantSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(read_only=True)

    class Meta:
        model = Usuario
        fields = ['id', 'email', 'first_name', 'last_name', 'avatar', 'rol']


class MessageSerializer(serializers.ModelSerializer):
    autor = ChatParticipantSerializer(read_only=True)
    es_mio = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'autor', 'contenido', 'leido', 'creado', 'es_mio']
        read_only_fields = ['id', 'autor', 'leido', 'creado', 'es_mio']

    def get_es_mio(self, obj: Message) -> bool:
        request = self.context.get('request')
        return bool(request and request.user.is_authenticated and obj.autor_id == request.user.id)


class ConversationSerializer(serializers.ModelSerializer):
    participantes = ChatParticipantSerializer(many=True, read_only=True)
    ultimo_mensaje = serializers.SerializerMethodField()
    no_leidos = serializers.SerializerMethodField()
    producto = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Conversation
        fields = ['id', 'participantes', 'producto', 'ultimo_mensaje', 'no_leidos', 'creado', 'actualizado']

    @extend_schema_field(ConversationLastMessageSerializer(allow_null=True))
    def get_ultimo_mensaje(self, obj: Conversation) -> dict[str, Any] | None:
        msg = obj.mensajes.order_by('-creado').first()
        if not msg:
            return None
        return {
            'id': msg.id,
            'contenido': msg.contenido,
            'autor_id': msg.autor_id,
            'creado': msg.creado,
            'leido': msg.leido,
        }

    def get_no_leidos(self, obj: Conversation) -> int:
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        return obj.mensajes.filter(leido=False).exclude(autor=request.user).count()


class ConversationCreateSerializer(serializers.Serializer):
    """Inicia o recupera una conversación con otro usuario, opcionalmente sobre un producto."""

    destinatario_id = serializers.IntegerField(required=False)
    producto_id = serializers.IntegerField(required=False)

    def validate(self, attrs):
        if not attrs.get('destinatario_id') and not attrs.get('producto_id'):
            raise serializers.ValidationError('Debes indicar destinatario_id o producto_id.')
        return attrs


class ExpoPushTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpoPushToken
        fields = ['id', 'token', 'plataforma', 'creado']
        read_only_fields = ['id', 'creado']


class TasaCambioSerializer(serializers.ModelSerializer):
    registrado_por_email = serializers.CharField(
        source='registrado_por.email', read_only=True, default=None
    )

    class Meta:
        model = TasaCambio
        fields = ['id', 'valor_bs', 'fuente', 'creado', 'registrado_por_email']
        read_only_fields = ['id', 'creado', 'registrado_por_email']

    def validate_valor_bs(self, value):
        if value <= 0:
            raise serializers.ValidationError('La tasa debe ser mayor a 0.')
        return value


class StoreDashboardSerializer(serializers.Serializer):
    """Schema-only: la respuesta real se arma en la vista."""

    rango_dias = serializers.IntegerField()
    ingresos_usd = serializers.DecimalField(max_digits=14, decimal_places=2)
    ingresos_ves = serializers.DecimalField(max_digits=16, decimal_places=2)
    ordenes_total = serializers.IntegerField()
    ordenes_por_estado = serializers.DictField(child=serializers.IntegerField())
    productos_top = serializers.ListField(child=serializers.DictField())
    serie_diaria = serializers.ListField(child=serializers.DictField())
    tasa_vigente = TasaCambioSerializer(allow_null=True)
