from decimal import Decimal

from rest_framework import serializers
from .models import (
    Producto,
    Categoria,
    ItemCarrito,
    Carrito,
    Pedido,
    Tienda,
    ProductoTienda,
    Comentario,
    ComentarioProducto,
    Referencia,
    Wallet,
    Usuario,
    StoreOrder,
)

class UsuarioSerializer(serializers.ModelSerializer):
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

    class Meta:
        model = ItemCarrito
        fields = ['id', 'producto', 'cantidad', 'subtotal']

class CarritoSerializer(serializers.ModelSerializer):
    items = ItemCarritoSerializer(many=True, read_only=True)

    class Meta:
        model = Carrito
        fields = ['id', 'usuario', 'items', 'creado']

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
    edad = serializers.IntegerField(required=False, allow_null=True)
    cedula_pasaporte = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    foto_identificacion = serializers.FileField(
        required=False, allow_null=True, use_url=False
    )
    nombre_tienda = serializers.CharField(required=False, allow_blank=True)
    direccion = serializers.CharField(required=False, allow_blank=True)
    telefono_tienda = serializers.CharField(required=False, allow_blank=True)
    informacion_fiscal = serializers.CharField(required=False, allow_blank=True)
    ingresos_minimos_mensuales = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )


class CarritoItemAddSerializer(serializers.Serializer):
    producto_id = serializers.IntegerField()
    cantidad = serializers.IntegerField(required=False, min_value=1, default=1)


class CarritoItemRemoveSerializer(serializers.Serializer):
    producto_id = serializers.IntegerField()


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
            'estado',
            'creado',
            'actualizado',
        ]
