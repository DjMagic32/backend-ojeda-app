from rest_framework import serializers
from .models import (
    Producto, Categoria, ItemCarrito, Carrito, Pedido, Tienda, ProductoTienda,
    Comentario, ComentarioProducto, Referencia, Wallet, Usuario,
    ChatRoom, ChatMessage, ExchangeProposal # Added ExchangeProposal
)

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
    # Ensure 'usuario' is read-only or handled appropriately if set by request.user
    # For 'tienda', it might be set based on items or explicitly.

    class Meta:
        model = Pedido
        fields = [
            'id', 'usuario', 'tienda', 'items', 'total', 'creado',
            'estado_pago', 'payment_intent_id', 'binance_order_id'
        ]
        read_only_fields = ('usuario', 'total', 'estado_pago', 'payment_intent_id', 'binance_order_id')


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.ReadOnlyField(source='sender.username')

    class Meta:
        model = ChatMessage
        fields = ['id', 'room', 'sender', 'sender_username', 'content', 'timestamp', 'message_type']
        read_only_fields = ('sender', 'timestamp', 'sender_username') # Room is set by URL or context

class ChatRoomSerializer(serializers.ModelSerializer):
    participants = UsuarioSerializer(many=True, read_only=True)
    # last_message = ChatMessageSerializer(read_only=True) # Potentially heavy, consider a lighter version or method field
    unread_count = serializers.SerializerMethodField() # Example: if you implement unread counts

    class Meta:
        model = ChatRoom
        fields = ['id', 'participants', 'created_at', 'updated_at', 'unread_count'] # Add 'last_message' if you implement it
        read_only_fields = ('created_at', 'updated_at')

    def get_unread_count(self, obj):
        # Placeholder: Actual unread count logic would be more complex
        # e.g., based on a 'last_read_timestamp' per user per room.
        # user = self.context['request'].user
        # return ChatMessage.objects.filter(room=obj, timestamp__gt=user.last_read_in_room.get(obj.id, timezone.now()-timedelta(days=365))).count()
        return 0

class ExchangeProposalSerializer(serializers.ModelSerializer):
    proposing_user_details = UsuarioSerializer(source='proposing_user', read_only=True)
    proposed_product_details = ProductoSerializer(source='proposed_product', read_only=True)
    # We need to make chat_room writeable for creation, but read_only for display might be through a nested URL.
    # For creation, client will need to specify chat_room ID.

    class Meta:
        model = ExchangeProposal
        fields = [
            'id', 'chat_room', 'proposing_user', 'proposing_user_details',
            'proposed_product', 'proposed_product_details', 'quantity', 'price', 'terms',
            'status', 'created_at', 'updated_at', 'initiating_message'
        ]
        read_only_fields = ('proposing_user', 'status', 'created_at', 'updated_at', 'initiating_message', 'proposing_user_details', 'proposed_product_details')

    def create(self, validated_data):
        request = self.context.get('request')
        proposing_user = request.user
        chat_room = validated_data.get('chat_room')

        # Validate that the proposing_user is a participant of the chat_room
        if not chat_room.participants.filter(id=proposing_user.id).exists():
            raise serializers.ValidationError("You are not a participant of this chat room and cannot make proposals.")

        # Create the proposal
        proposal = ExchangeProposal.objects.create(proposing_user=proposing_user, **validated_data)

        # Optionally, create an initial ChatMessage of type 'proposal_initiate'
        # This message can link to the proposal.
        # chat_message = ChatMessage.objects.create(
        #     room=chat_room,
        #     sender=proposing_user,
        #     message_type=ChatMessage.MESSAGE_TYPE_PROPOSAL_INITIATE,
        #     content=f"Propuesta de intercambio: {proposal.proposed_product.name if proposal.proposed_product else 'item/servicio'}"
        # )
        # proposal.initiating_message = chat_message
        # proposal.save()

        # TODO: Trigger WebSocket notification about the new proposal (will be handled in a later step)
        return proposal

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