from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView
from .models import Producto, Categoria, Carrito, ItemCarrito, Pedido, Tienda, ProductoTienda, Comentario, ComentarioProducto, Referencia, Wallet, Usuario
from .serializers import ProductoSerializer, CategoriaSerializer, CarritoSerializer, ItemCarritoSerializer, PedidoSerializer, TiendaSerializer, ProductoTiendaSerializer, ComentarioSerializer, ComentarioProductoSerializer, ReferenciaSerializer, WalletSerializer, UsuarioSerializer
from .permissions import EsTienda

class CreateUserView(APIView):
    permission_classes = [permissions.AllowAny]  # Permitir acceso sin necesidad de token

    def post(self, request, *args, **kwargs):
        serializer = UsuarioSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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