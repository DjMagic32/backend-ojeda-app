from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView
from .models import Producto, Categoria, Carrito, ItemCarrito, Pedido, Tienda, ProductoTienda, Comentario, ComentarioProducto, Referencia, Wallet, Usuario
from .serializers import (
    ProductoSerializer, CategoriaSerializer, CarritoSerializer, ItemCarritoSerializer,
    PedidoSerializer, TiendaSerializer, ProductoTiendaSerializer, ComentarioSerializer,
    ComentarioProductoSerializer, ReferenciaSerializer, WalletSerializer, UsuarioSerializer,
    WalletActionSerializer
)
from .permissions import EsTienda

class CreateUserView(APIView):
    permission_classes = [permissions.AllowAny]  # Permitir acceso sin token

    def post(self, request, *args, **kwargs):
        serializer = UsuarioSerializer(data=request.data)
        if serializer.is_valid():
            # The email uniqueness check is now handled by the serializer if 'email' has UniqueValidator
            # or if the model field 'email' unique=True is respected by ModelSerializer.
            # The manual check can be removed:
            # email = data.get('email', '').strip().lower()
            # if Usuario.objects.filter(email=email).exists():
            #     return Response({'error': 'El correo ya está en uso.'}, status=status.HTTP_400_BAD_REQUEST)

            user = serializer.save() # The serializer's create method handles password hashing and username

            # Logic for Tienda creation
            if user.rol == Usuario.ES_TIENDA:
                tienda_data = {
                    'usuario': user.id, # Use user.id from the saved instance
                    'nombre': request.data.get('nombre_tienda', ''),
                    'direccion': request.data.get('direccion', ''),
                    'telefono': request.data.get('telefono_tienda', ''),
                    'informacion_fiscal': request.data.get('informacion_fiscal', ''),
                }
                tienda_serializer = TiendaSerializer(data=tienda_data)
                if tienda_serializer.is_valid():
                    tienda_serializer.save()
                    # Return the user serializer data (which now excludes password)
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
                else:
                    user.delete()  # Clean up created user if tienda creation fails
                    return Response(tienda_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class UsuarioViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer

class CategoriaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer

class ProductoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Producto.objects.select_related('categoria').all()
    serializer_class = ProductoSerializer

class CarritoView(APIView):
    '''Handles operations related to the user's shopping cart.'''
    permission_classes = [IsAuthenticated]
    def get(self, request):
        carrito, _ = Carrito.objects.prefetch_related('items__producto').get_or_create(usuario=request.user)
        serializer = CarritoSerializer(carrito)
        return Response(serializer.data)

    def post(self, request):
        carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
        producto = Producto.objects.get(id=request.data['producto_id'])
        item, created = ItemCarrito.objects.get_or_create(carrito=carrito, producto=producto)
        if not created:
            item.cantidad += request.data.get('cantidad', 1)
            item.save()
        serializer = CarritoSerializer(carrito)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request):
        carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
        producto = Producto.objects.get(id=request.data['producto_id'])
        item = ItemCarrito.objects.get(carrito=carrito, producto=producto)
        item.delete()
        serializer = CarritoSerializer(carrito)
        return Response(serializer.data)

class PedidoView(APIView):
    '''Manages creating new orders from the cart and listing user's orders.'''
    permission_classes = [IsAuthenticated]
    def post(self, request):
        carrito = Carrito.objects.get(usuario=request.user)
        items = carrito.items.all()
        if not items:
            return Response({'error': 'El carrito está vacío.'}, status=status.HTTP_400_BAD_REQUEST)

        total = sum(item.subtotal for item in items)
        pedido = Pedido.objects.create(usuario=request.user, total=total)
        pedido.items.set(items)
        carrito.items.all().delete()  # Vaciar el carrito
        serializer = PedidoSerializer(pedido)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request):
        pedidos = Pedido.objects.filter(usuario=request.user).prefetch_related('items__producto')
        serializer = PedidoSerializer(pedidos, many=True)
        return Response(serializer.data)

class TiendaViewSet(viewsets.ModelViewSet):
    
    permission_classes = [IsAuthenticated, EsTienda]
    queryset = Tienda.objects.select_related('usuario').all()
    serializer_class = TiendaSerializer

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

class ProductoTiendaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, EsTienda]
    queryset = ProductoTienda.objects.select_related('tienda__usuario').all()
    serializer_class = ProductoTiendaSerializer

    def perform_create(self, serializer):
        # Assumes that a Tienda instance already exists for this user,
        # which should be ensured during user registration if rol is TIENDA.
        tienda = Tienda.objects.get(usuario=self.request.user)
        serializer.save(tienda=tienda)

class ComentarioViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Comentario.objects.select_related('tienda', 'usuario').all()
    serializer_class = ComentarioSerializer

class ComentarioProductoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ComentarioProducto.objects.select_related('usuario', 'producto__categoria').all()
    serializer_class = ComentarioProductoSerializer

class ReferenciaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Referencia.objects.select_related('usuario', 'tienda', 'producto__categoria').all()
    serializer_class = ReferenciaSerializer

class WalletViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer

class WalletActionView(APIView):
    '''Allows users to perform actions on their wallet, primarily adding funds.'''
    permission_classes = [IsAuthenticated]
    def post(self, request):
        action_serializer = WalletActionSerializer(data=request.data)
        if action_serializer.is_valid():
            wallet, _ = Wallet.objects.get_or_create(usuario=request.user) # Consider get_or_create
            amount = action_serializer.validated_data['amount'] # Use validated data

            # Add logic here if you need to distinguish between deposit/withdrawal based on amount or another field
            wallet.saldo += amount
            wallet.save()

            response_serializer = WalletSerializer(wallet)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        return Response(action_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class UsuarioDetalleView(APIView):
    '''Provides detailed information about the authenticated user, including Tienda details if applicable.'''
    permission_classes = [IsAuthenticated]
    def post(self, request):
        # Autenticar el usuario usando el token
        user = request.user  # Dado que estamos usando JWT, el usuario ya está autenticado

        # Serializar la información del usuario
        usuario_serializer = UsuarioSerializer(user)

        # Eliminar la contraseña de los datos serializados
        usuario_data = usuario_serializer.data
        # if 'password' in usuario_data: # This block can be removed
        #     del usuario_data['password']

        # Verificar si el usuario es una tienda
        tienda_data = None
        if user.rol == Usuario.ES_TIENDA:
            try:
                tienda = Tienda.objects.get(usuario=user)
                tienda_serializer = TiendaSerializer(tienda)
                tienda_data = tienda_serializer.data
            except Tienda.DoesNotExist:
                return Response({'error': 'Tienda no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        # Devolver los datos del usuario y, si es una tienda, también los de la tienda
        response_data = usuario_data
        if tienda_data:
            response_data['tienda'] = tienda_data

        return Response(response_data, status=status.HTTP_200_OK)
