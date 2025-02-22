from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView
from .models import Producto, Categoria, Carrito, ItemCarrito, Pedido, Tienda, ProductoTienda, Comentario, ComentarioProducto, Referencia, Wallet, Usuario
from .serializers import ProductoSerializer, CategoriaSerializer, CarritoSerializer, ItemCarritoSerializer, PedidoSerializer, TiendaSerializer, ProductoTiendaSerializer, ComentarioSerializer, ComentarioProductoSerializer, ReferenciaSerializer, WalletSerializer, UsuarioSerializer
from .permissions import EsTienda

class CreateUserView(APIView):
    permission_classes = [permissions.AllowAny]  # Permitir acceso sin token

    def post(self, request, *args, **kwargs):
        data = request.data.copy()  # Creamos una copia de los datos del request
        email = data.get('email', '').strip().lower()  # Convertimos el email a minúsculas

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

class CarritoView(APIView):
    #permission_classes = [IsAuthenticated]
    def get(self, request):
        carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
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
    #permission_classes = [IsAuthenticated]
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
    #permission_classes = [EsTienda, IsAuthenticated]
    queryset = ProductoTienda.objects.all()
    serializer_class = ProductoTiendaSerializer

    def perform_create(self, serializer):
        tienda = Tienda.objects.get(usuario=self.request.user)
        serializer.save(tienda=tienda)

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

class WalletActionView(APIView):
    #permission_classes = [IsAuthenticated]
    def post(self, request):
        wallet = Wallet.objects.get(usuario=request.user)
        amount = request.data.get('amount', 0)
        wallet.saldo += amount
        wallet.save()
        serializer = WalletSerializer(wallet)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class UsuarioDetalleView(APIView):
    def post(self, request):
        # Obtener el token del cuerpo de la solicitud (request.data)
        token = request.data.get('token', None)
        if not token:
            return Response({'error': 'Token no proporcionado'}, status=status.HTTP_400_BAD_REQUEST)

        # Autenticar el usuario usando el token
        user = request.user  # Dado que estamos usando JWT, el usuario ya está autenticado

        if not user:
            return Response({'error': 'Usuario no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        # Serializar la información del usuario
        usuario_serializer = UsuarioSerializer(user)

        # Eliminar la contraseña de los datos serializados
        usuario_data = usuario_serializer.data
        if 'password' in usuario_data:
            del usuario_data['password']

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
