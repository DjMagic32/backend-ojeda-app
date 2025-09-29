from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, status, permissions, generics
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import extend_schema

from .models import (
    Producto,
    Categoria,
    Carrito,
    ItemCarrito,
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
from .serializers import (
    ProductoSerializer,
    CategoriaSerializer,
    CarritoSerializer,
    ItemCarritoSerializer,
    PedidoSerializer,
    TiendaSerializer,
    ProductoTiendaSerializer,
    ComentarioSerializer,
    ComentarioProductoSerializer,
    ReferenciaSerializer,
    WalletSerializer,
    UsuarioSerializer,
    RegisterUserSerializer,
    CarritoItemAddSerializer,
    CarritoItemRemoveSerializer,
    WalletActionRequestSerializer,
    UsuarioDetalleRequestSerializer,
    StoreOrderSerializer,
)
from .permissions import EsTienda


class CreateUserView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = UsuarioSerializer

    @extend_schema(
        request=RegisterUserSerializer,
        responses=UsuarioSerializer,
        description="Registra un nuevo usuario y opcionalmente su tienda asociada.",
    )
    def post(self, request, *args, **kwargs):
        serializer = RegisterUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        email = data.get('email', '').strip().lower()

        # Verificamos si el email ya está en uso
        if Usuario.objects.filter(email=email).exists():
            return Response({'error': 'El correo ya está en uso.'}, status=status.HTTP_400_BAD_REQUEST)

        data['email'] = email  # Guardamos el email en minúsculas
        data['username'] = email  # Usamos el email como username

        # Creamos el usuario manualmente sin guardarlo aún
        usuario = Usuario(
            email=email,
            username=email,
            first_name=data.get('nombre', ''),  # Corregimos el nombre
            last_name=data.get('apellido', ''),  # Corregimos el apellido
            rol=data.get('rol', Usuario.ES_CLIENTE),  # Valor por defecto
            telefono=data.get('telefono', ''),  # Agregamos el teléfono
            genero=data.get('genero', None),  # Agregamos el género
            edad=data.get('edad', None),  # Agregamos la edad
            cedula_pasaporte=data.get('cedula_pasaporte', None),  # Agregamos la cédula/pasaporte
        )
        usuario.set_password(data['password'])  # Hasheamos la contraseña
        usuario.save()  # Guardamos el usuario en la base de datos

        # Si el usuario es de tipo TIENDA, creamos también la tienda
        if usuario.rol == Usuario.ES_TIENDA:
            tienda_data = {
                'usuario': usuario.id,
                'nombre': data.get('nombre_tienda', ''),
                'direccion': data.get('direccion', ''),
                'telefono': data.get('telefono_tienda', ''),
                'informacion_fiscal': data.get('informacion_fiscal', ''),
            }
            tienda_serializer = TiendaSerializer(data=tienda_data)
            if tienda_serializer.is_valid():
                tienda_serializer.save()
            else:
                usuario.delete()  # Eliminamos el usuario si la tienda falla
                return Response(tienda_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Serializamos el usuario ya creado para devolverlo en la respuesta
        usuario_serializer = UsuarioSerializer(usuario)
        return Response(usuario_serializer.data, status=status.HTTP_201_CREATED)
    

class UsuarioViewSet(viewsets.ModelViewSet):
    #permission_classes = [IsAuthenticated]
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer

class CategoriaViewSet(viewsets.ModelViewSet):
    #permission_classes = [IsAuthenticated]
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer

class ProductoViewSet(viewsets.ModelViewSet):
    #permission_classes = [IsAuthenticated]
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

class CarritoView(generics.GenericAPIView):
    serializer_class = CarritoSerializer
    # permission_classes = [IsAuthenticated]

    @extend_schema(responses=CarritoSerializer)
    def get(self, request):
        carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
        serializer = CarritoSerializer(carrito)
        return Response(serializer.data)

    @extend_schema(request=CarritoItemAddSerializer, responses=CarritoSerializer)
    def post(self, request):
        payload = CarritoItemAddSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
        producto_id = payload.validated_data['producto_id']
        cantidad = payload.validated_data.get('cantidad', 1)

        try:
            producto = Producto.objects.get(id=producto_id)
        except Producto.DoesNotExist:
            return Response(
                {'error': 'Producto no encontrado'},
                status=status.HTTP_404_NOT_FOUND,
            )

        item, created = ItemCarrito.objects.get_or_create(
            carrito=carrito, producto=producto
        )
        if not created:
            item.cantidad += cantidad
            item.save()

        serializer = CarritoSerializer(carrito)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(request=CarritoItemRemoveSerializer, responses=CarritoSerializer)
    def delete(self, request):
        payload = CarritoItemRemoveSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
        producto_id = payload.validated_data['producto_id']

        try:
            producto = Producto.objects.get(id=producto_id)
        except Producto.DoesNotExist:
            return Response(
                {'error': 'Producto no encontrado'},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            item = ItemCarrito.objects.get(carrito=carrito, producto=producto)
        except ItemCarrito.DoesNotExist:
            return Response(
                {'error': 'El producto no está en el carrito'},
                status=status.HTTP_404_NOT_FOUND,
            )

        item.delete()
        serializer = CarritoSerializer(carrito)
        return Response(serializer.data)

class PedidoView(generics.GenericAPIView):
    serializer_class = PedidoSerializer
    # permission_classes = [IsAuthenticated]

    @extend_schema(responses=PedidoSerializer)
    def post(self, request):
        carrito = Carrito.objects.get(usuario=request.user)
        items = carrito.items.all()
        if not items:
            return Response(
                {'error': 'El carrito está vacío.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        total = sum(item.subtotal for item in items)
        pedido = Pedido.objects.create(usuario=request.user, total=total)
        pedido.items.set(items)
        carrito.items.all().delete()
        serializer = PedidoSerializer(pedido)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(responses=PedidoSerializer(many=True))
    def get(self, request):
        pedidos = Pedido.objects.filter(usuario=request.user)
        serializer = PedidoSerializer(pedidos, many=True)
        return Response(serializer.data)

class TiendaViewSet(viewsets.ModelViewSet):
    
    #permission_classes = [EsTienda, IsAuthenticated]
    queryset = Tienda.objects.all()
    serializer_class = TiendaSerializer

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

class ProductoTiendaViewSet(viewsets.ModelViewSet):
    queryset = ProductoTienda.objects.select_related('tienda', 'tienda__usuario')
    serializer_class = ProductoTiendaSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [permissions.AllowAny]

    def _get_tienda_for_request(self):
        try:
            return Tienda.objects.get(usuario=self.request.user)
        except Tienda.DoesNotExist as exc:
            raise ValidationError('El usuario autenticado no tiene una tienda asociada.') from exc

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            scope = self.request.query_params.get('scope')
            if scope == 'mine':
                return [IsAuthenticated(), EsTienda()]
            return [permissions.AllowAny()]
        return [IsAuthenticated(), EsTienda()]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        scope = self.request.query_params.get('scope')

        if user.is_authenticated and getattr(user, 'rol', None) == Usuario.ES_TIENDA:
            if scope == 'mine':
                try:
                    tienda = Tienda.objects.get(usuario=user)
                except Tienda.DoesNotExist:
                    return ProductoTienda.objects.none()
                return queryset.filter(tienda=tienda)
            # scope == 'all' or default -> return full queryset
        return queryset

    def perform_create(self, serializer):
        tienda = self._get_tienda_for_request()
        serializer.save(tienda=tienda)

    def perform_update(self, serializer):
        tienda = self._get_tienda_for_request()
        serializer.save(tienda=tienda)


class StoreOrderViewSet(viewsets.ModelViewSet):
    serializer_class = StoreOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        scope = self.request.query_params.get('scope')

        base_queryset = StoreOrder.objects.select_related(
            'producto', 'producto__tienda', 'usuario'
        )

        if scope == 'store' and getattr(user, 'rol', None) == Usuario.ES_TIENDA:
            return base_queryset.filter(producto__tienda__usuario=user)

        return base_queryset.filter(usuario=user)

    def perform_create(self, serializer):
        user = self.request.user
        producto = serializer.validated_data['producto']
        cantidad = serializer.validated_data.get('cantidad', 1)

        precio_unitario = producto.precio
        total = precio_unitario * cantidad

        serializer.save(
            usuario=user,
            precio_unitario=precio_unitario,
            total=total,
            estado=StoreOrder.ESTADO_PENDIENTE,
        )

class ComentarioViewSet(viewsets.ModelViewSet):
    #permission_classes = [IsAuthenticated]
    queryset = Comentario.objects.all()
    serializer_class = ComentarioSerializer

class ComentarioProductoViewSet(viewsets.ModelViewSet):
    #permission_classes = [IsAuthenticated]
    queryset = ComentarioProducto.objects.all()
    serializer_class = ComentarioProductoSerializer

class ReferenciaViewSet(viewsets.ModelViewSet):
    #permission_classes = [IsAuthenticated]
    queryset = Referencia.objects.all()
    serializer_class = ReferenciaSerializer

class WalletViewSet(viewsets.ModelViewSet):
    #permission_classes = [IsAuthenticated]
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer

class WalletActionView(generics.GenericAPIView):
    serializer_class = WalletSerializer
    # permission_classes = [IsAuthenticated]

    @extend_schema(
        request=WalletActionRequestSerializer,
        responses=WalletSerializer,
    )
    def post(self, request):
        wallet = Wallet.objects.get(usuario=request.user)
        payload = WalletActionRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        amount = payload.validated_data['amount']
        wallet.saldo += amount
        wallet.save()
        serializer = WalletSerializer(wallet)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UsuarioDetalleView(generics.GenericAPIView):
    serializer_class = UsuarioSerializer

    @extend_schema(
        request=UsuarioDetalleRequestSerializer,
        responses=UsuarioSerializer,
    )
    def post(self, request):
        payload = UsuarioDetalleRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        token = payload.validated_data.get('token')
        if not token:
            return Response(
                {'error': 'Token no proporcionado'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user

        if not user or not user.is_authenticated:
            return Response(
                {'error': 'Usuario no encontrado'},
                status=status.HTTP_404_NOT_FOUND,
            )

        usuario_serializer = UsuarioSerializer(user)
        usuario_data = usuario_serializer.data
        usuario_data.pop('password', None)

        if user.rol == Usuario.ES_TIENDA:
            try:
                tienda = Tienda.objects.get(usuario=user)
            except Tienda.DoesNotExist:
                return Response(
                    {'error': 'Tienda no encontrada'},
                    status=status.HTTP_404_NOT_FOUND,
                )

            tienda_serializer = TiendaSerializer(tienda)
            usuario_data['tienda'] = tienda_serializer.data

        return Response(usuario_data, status=status.HTTP_200_OK)
