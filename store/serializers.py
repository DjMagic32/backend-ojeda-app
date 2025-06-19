from rest_framework import serializers
from .models import Producto, Categoria, ItemCarrito, Carrito, Pedido, Tienda, ProductoTienda, Comentario, ComentarioProducto, Referencia, Wallet, Usuario

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'rol', 'edad', 'genero', 'telefono', 'cedula_pasaporte', 'foto_identificacion', 'ingresos_minimos_mensuales', 'password']
        extra_kwargs = {
            'password': {'write_only': True, 'style': {'input_type': 'password'}}
        }

    def create(self, validated_data):
        # Ensure 'username' is present if not already handled by model/signals
        if 'username' not in validated_data and 'email' in validated_data:
            validated_data['username'] = validated_data['email']
        user = Usuario.objects.create_user(**validated_data)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        # Handle username update if email changes and username is tied to email
        if 'email' in validated_data and validated_data.get('username') == instance.email:
             validated_data['username'] = validated_data['email']
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

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

from decimal import Decimal

class WalletActionSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    # Add more specific validation like min_value if needed, e.g.
    # amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))

    def validate_amount(self, value):
        if value <= Decimal('0.00'): # Example: disallow zero or negative amounts for a generic 'add funds' action
            raise serializers.ValidationError("Amount must be positive.")
        return value