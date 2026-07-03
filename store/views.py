from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import viewsets, status, permissions, generics
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import extend_schema

from django.db.models import Q
from rest_framework.decorators import action

from .models import (
    Producto,
    Categoria,
    Conversation,
    ExpoPushToken,
    Carrito,
    ItemCarrito,
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
from .serializers import (
    ProductoSerializer,
    CategoriaSerializer,
    CarritoSerializer,
    ConversationCreateSerializer,
    ConversationSerializer,
    ExpoPushTokenSerializer,
    ItemCarritoSerializer,
    MessageSerializer,
    PedidoSerializer,
    StoreDashboardSerializer,
    TasaCambioSerializer,
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
    CarritoItemUpdateSerializer,
    WalletActionRequestSerializer,
    UsuarioDetalleRequestSerializer,
    StoreOrderSerializer,
    ProductoFavoritoSerializer,
    NotificacionSerializer,
)
from .permissions import EsTienda
from .services.realtime import broadcast_chat_message, broadcast_chat_read, notify_user
from .services.push import send_push_to_user


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
    permission_classes = [AllowAny]
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer

class ProductoViewSet(viewsets.ModelViewSet):
    #permission_classes = [IsAuthenticated]
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

class CarritoView(generics.GenericAPIView):
    serializer_class = CarritoSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=CarritoSerializer)
    def get(self, request):
        # Debug auth
        user = getattr(request, "user", None)
        print("[CarritoView][GET] user:", user, "is_authenticated:", getattr(user, "is_authenticated", False))
        carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
        serializer = CarritoSerializer(carrito)
        return Response(serializer.data)

    @extend_schema(request=CarritoItemAddSerializer, responses=CarritoSerializer)
    def post(self, request):
        user = getattr(request, "user", None)
        print("[CarritoView][POST] user:", user, "is_authenticated:", getattr(user, "is_authenticated", False))
        payload = CarritoItemAddSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
        producto_id = payload.validated_data['producto_id']
        cantidad = payload.validated_data.get('cantidad', 1)

        try:
            producto = ProductoTienda.objects.get(id=producto_id)
        except ProductoTienda.DoesNotExist:
            return Response(
                {'error': 'Producto no encontrado'},
                status=status.HTTP_404_NOT_FOUND,
            )

        item, created = ItemCarrito.objects.get_or_create(
            carrito=carrito, producto_tienda=producto
        )
        if not created:
            item.cantidad += cantidad
            item.save()

        serializer = CarritoSerializer(carrito)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(request=CarritoItemUpdateSerializer, responses=CarritoSerializer)
    def patch(self, request):
        user = getattr(request, "user", None)
        print("[CarritoView][PATCH] user:", user, "is_authenticated:", getattr(user, "is_authenticated", False))
        payload = CarritoItemUpdateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
        producto_id = payload.validated_data['producto_id']
        cantidad = payload.validated_data['cantidad']

        try:
            producto = ProductoTienda.objects.get(id=producto_id)
        except ProductoTienda.DoesNotExist:
            return Response(
                {'error': 'Producto no encontrado'},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            item = ItemCarrito.objects.get(carrito=carrito, producto_tienda=producto)
        except ItemCarrito.DoesNotExist:
            return Response(
                {'error': 'El producto no está en el carrito'},
                status=status.HTTP_404_NOT_FOUND,
            )

        item.cantidad = cantidad
        item.save()
        serializer = CarritoSerializer(carrito)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(request=CarritoItemRemoveSerializer, responses=CarritoSerializer)
    def delete(self, request):
        user = getattr(request, "user", None)
        print("[CarritoView][DELETE] user:", user, "is_authenticated:", getattr(user, "is_authenticated", False))
        payload = CarritoItemRemoveSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
        producto_id = payload.validated_data['producto_id']

        try:
            producto = ProductoTienda.objects.get(id=producto_id)
        except ProductoTienda.DoesNotExist:
            return Response(
                {'error': 'Producto no encontrado'},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            item = ItemCarrito.objects.get(carrito=carrito, producto_tienda=producto)
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
    permission_classes = [IsAuthenticated]

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
    queryset = StoreOrder.objects.select_related('producto', 'producto__tienda', 'usuario')

    def get_queryset(self):
        user = self.request.user
        scope = self.request.query_params.get('scope')

        base_queryset = self.queryset

        if scope == 'store' and getattr(user, 'rol', None) == Usuario.ES_TIENDA:
            return base_queryset.filter(producto__tienda__usuario=user)

        return base_queryset.filter(usuario=user)

    def perform_create(self, serializer):
        user = self.request.user
        producto = serializer.validated_data['producto']
        cantidad = serializer.validated_data.get('cantidad', 1)

        precio_unitario = producto.precio
        total = precio_unitario * cantidad
        tasa = TasaCambio.vigente()

        serializer.save(
            usuario=user,
            precio_unitario=precio_unitario,
            total=total,
            moneda=producto.moneda,
            tasa_aplicada=tasa.valor_bs if tasa else None,
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


class UsuarioProfileUpdateView(generics.GenericAPIView):
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(request=UsuarioSerializer, responses=UsuarioSerializer)
    def patch(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({'error': 'Autenticación requerida'}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ProductoFavoritoView(generics.GenericAPIView):
    serializer_class = ProductoFavoritoSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=ProductoFavoritoSerializer(many=True))
    def get(self, request):
        user = getattr(request, "user", None)
        print("[Favoritos][GET] user:", user, "is_authenticated:", getattr(user, "is_authenticated", False))
        favoritos = ProductoFavorito.objects.filter(usuario=request.user).select_related('producto')
        serializer = ProductoFavoritoSerializer(favoritos, many=True)
        return Response(serializer.data)

    @extend_schema(request=ProductoFavoritoSerializer, responses=ProductoFavoritoSerializer)
    def post(self, request):
        user = getattr(request, "user", None)
        print("[Favoritos][POST] user:", user, "is_authenticated:", getattr(user, "is_authenticated", False))
        producto_id = request.data.get('producto')
        if not producto_id:
            return Response({'error': 'producto es requerido'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            producto = ProductoTienda.objects.get(pk=producto_id)
        except ProductoTienda.DoesNotExist:
            return Response({'error': 'Producto no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        favorito, _ = ProductoFavorito.objects.get_or_create(
            usuario=request.user,
            producto=producto,
        )
        Notificacion.objects.create(
            usuario=request.user,
            titulo='Producto agregado a favoritos',
            mensaje=f'{producto.nombre} ahora está en tu lista de favoritos.',
            tipo=Notificacion.TIPO_FAVORITO,
            leido=False,
        )
        serializer = ProductoFavoritoSerializer(favorito)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(request=ProductoFavoritoSerializer, responses=ProductoFavoritoSerializer)
    def delete(self, request):
        user = getattr(request, "user", None)
        print("[Favoritos][DELETE] user:", user, "is_authenticated:", getattr(user, "is_authenticated", False))
        producto_id = request.data.get('producto')
        if not producto_id:
            return Response({'error': 'producto es requerido'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            favorito = ProductoFavorito.objects.get(usuario=request.user, producto_id=producto_id)
        except ProductoFavorito.DoesNotExist:
            return Response({'error': 'Favorito no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        favorito.delete()
        try:
            producto = ProductoTienda.objects.get(pk=producto_id)
            Notificacion.objects.create(
                usuario=request.user,
                titulo='Producto removido de favoritos',
                mensaje=f'{producto.nombre} se quitó de tu lista de favoritos.',
                tipo=Notificacion.TIPO_FAVORITO,
                leido=False,
            )
        except ProductoTienda.DoesNotExist:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificacionListView(generics.GenericAPIView):
    serializer_class = NotificacionSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=NotificacionSerializer(many=True))
    def get(self, request):
        qs = Notificacion.objects.filter(usuario=request.user).order_by('-creado')
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class NotificacionUnreadCountView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={'application/json': {'type': 'object'}})
    def get(self, request):
        count = Notificacion.objects.filter(usuario=request.user, leido=False).count()
        return Response({'unread': count})


class NotificacionMarkReadView(generics.GenericAPIView):
    serializer_class = NotificacionSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=NotificacionSerializer)
    def post(self, request, pk: int):
        try:
            notificacion = Notificacion.objects.get(pk=pk, usuario=request.user)
        except Notificacion.DoesNotExist:
            return Response({'error': 'Notificación no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        if not notificacion.leido:
            notificacion.leido = True
            notificacion.save(update_fields=['leido'])

        serializer = self.get_serializer(notificacion)
        return Response(serializer.data)


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'delete', 'head', 'options']
    queryset = Conversation.objects.all()

    def get_queryset(self):
        return (
            Conversation.objects.filter(participantes=self.request.user)
            .prefetch_related('participantes', 'mensajes')
            .order_by('-actualizado')
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return ConversationCreateSerializer
        return ConversationSerializer

    def create(self, request, *args, **kwargs):
        payload = ConversationCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        destinatario_id = payload.validated_data.get('destinatario_id')
        producto_id = payload.validated_data.get('producto_id')

        producto = None
        if producto_id is not None:
            try:
                producto = ProductoTienda.objects.select_related('tienda', 'tienda__usuario').get(pk=producto_id)
            except ProductoTienda.DoesNotExist:
                return Response({'error': 'Producto no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
            if destinatario_id is None:
                destinatario_id = producto.tienda.usuario_id

        if destinatario_id == request.user.id:
            return Response({'error': 'No puedes chatear contigo mismo.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            destinatario = Usuario.objects.get(pk=destinatario_id)
        except Usuario.DoesNotExist:
            return Response({'error': 'Destinatario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        conversacion, _ = Conversation.get_or_create_between(request.user, destinatario, producto=producto)
        serializer = ConversationSerializer(conversacion, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get', 'post'], url_path='messages')
    def messages(self, request, pk: int | None = None):
        conversation = self.get_object()
        if request.method == 'GET':
            qs = conversation.mensajes.select_related('autor').order_by('creado')
            serializer = MessageSerializer(qs, many=True, context={'request': request})
            return Response(serializer.data)

        contenido = (request.data.get('contenido') or '').strip()
        if not contenido:
            return Response({'error': 'El mensaje no puede estar vacío.'}, status=status.HTTP_400_BAD_REQUEST)

        mensaje = Message.objects.create(
            conversation=conversation,
            autor=request.user,
            contenido=contenido,
        )
        conversation.save(update_fields=['actualizado'])

        data = MessageSerializer(mensaje, context={'request': request}).data
        broadcast_chat_message(conversation.id, data)

        # Notificar al otro participante (in-app + push)
        otros = conversation.participantes.exclude(id=request.user.id)
        autor_nombre = request.user.first_name or request.user.email
        for destinatario in otros:
            Notificacion.objects.create(
                usuario=destinatario,
                titulo=f'Nuevo mensaje de {autor_nombre}',
                mensaje=contenido[:140],
                tipo=Notificacion.TIPO_MENSAJE,
                data={'conversation_id': conversation.id},
                leido=False,
            )
            send_push_to_user(
                destinatario.id,
                title=f'Nuevo mensaje de {autor_nombre}',
                body=contenido[:140],
                data={'type': 'chat', 'conversation_id': conversation.id},
            )

        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='read')
    def mark_read(self, request, pk: int | None = None):
        conversation = self.get_object()
        updated = conversation.mensajes.filter(leido=False).exclude(autor=request.user).update(leido=True)
        if updated:
            broadcast_chat_read(conversation.id, request.user.id)
        return Response({'updated': updated})


class TasaCambioView(generics.GenericAPIView):
    """Endpoint público para leer la tasa vigente; sólo staff puede registrar nuevas."""

    serializer_class = TasaCambioSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return [permissions.AllowAny()]

    @extend_schema(responses=TasaCambioSerializer)
    def get(self, request):
        tasa = TasaCambio.vigente()
        if not tasa:
            return Response({'detail': 'Aún no hay tasa registrada.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.get_serializer(tasa).data)

    @extend_schema(request=TasaCambioSerializer, responses=TasaCambioSerializer)
    def post(self, request):
        if not request.user.is_staff:
            return Response(
                {'error': 'Sólo personal autorizado puede registrar tasas.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(registrado_por=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TasaCambioHistoryView(generics.ListAPIView):
    """Historial reciente de tasas (últimas 30)."""

    serializer_class = TasaCambioSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return TasaCambio.objects.all()[:30]


class StoreDashboardView(generics.GenericAPIView):
    """Métricas agregadas para el dueño de la tienda autenticado."""

    serializer_class = StoreDashboardSerializer
    permission_classes = [IsAuthenticated, EsTienda]

    @extend_schema(responses=StoreDashboardSerializer)
    def get(self, request):
        from datetime import timedelta
        from decimal import Decimal
        from django.db.models import Count, Sum
        from django.db.models.functions import TruncDate
        from django.utils import timezone

        try:
            rango_dias = int(request.query_params.get('dias', 30))
        except (TypeError, ValueError):
            rango_dias = 30
        rango_dias = max(1, min(rango_dias, 365))

        desde = timezone.now() - timedelta(days=rango_dias)
        ordenes_tienda = StoreOrder.objects.filter(
            producto__tienda__usuario=request.user,
            creado__gte=desde,
        )

        # Ingresos (sólo órdenes completadas), por moneda
        completadas = ordenes_tienda.filter(estado=StoreOrder.ESTADO_COMPLETADO)
        ingresos_por_moneda = {
            row['moneda']: row['total']
            for row in completadas.values('moneda').annotate(total=Sum('total'))
        }
        ingresos_usd = ingresos_por_moneda.get('USD') or Decimal('0')
        ingresos_ves = ingresos_por_moneda.get('VES') or Decimal('0')

        # Conteo por estado
        ordenes_por_estado = {
            estado: 0 for estado, _ in StoreOrder.ESTADOS
        }
        for row in ordenes_tienda.values('estado').annotate(n=Count('id')):
            ordenes_por_estado[row['estado']] = row['n']

        ordenes_total = sum(ordenes_por_estado.values())

        # Top 5 productos por cantidad vendida (sobre completadas)
        productos_top_qs = (
            completadas.values('producto__id', 'producto__nombre', 'moneda')
            .annotate(cantidad=Sum('cantidad'), ingreso=Sum('total'))
            .order_by('-cantidad')[:5]
        )
        productos_top = [
            {
                'producto_id': row['producto__id'],
                'nombre': row['producto__nombre'],
                'cantidad': row['cantidad'],
                'ingreso': str(row['ingreso']),
                'moneda': row['moneda'],
            }
            for row in productos_top_qs
        ]

        # Serie diaria de órdenes (todas, no sólo completadas) para el rango
        serie_qs = (
            ordenes_tienda.annotate(dia=TruncDate('creado'))
            .values('dia')
            .annotate(n=Count('id'), ingreso_usd=Sum('total', filter=Q(moneda='USD')),
                      ingreso_ves=Sum('total', filter=Q(moneda='VES')))
            .order_by('dia')
        )
        serie_diaria = [
            {
                'dia': row['dia'].isoformat() if row['dia'] else None,
                'ordenes': row['n'],
                'ingreso_usd': str(row['ingreso_usd'] or 0),
                'ingreso_ves': str(row['ingreso_ves'] or 0),
            }
            for row in serie_qs
        ]

        tasa = TasaCambio.vigente()
        tasa_data = TasaCambioSerializer(tasa).data if tasa else None

        return Response({
            'rango_dias': rango_dias,
            'ingresos_usd': str(ingresos_usd),
            'ingresos_ves': str(ingresos_ves),
            'ordenes_total': ordenes_total,
            'ordenes_por_estado': ordenes_por_estado,
            'productos_top': productos_top,
            'serie_diaria': serie_diaria,
            'tasa_vigente': tasa_data,
        })


class ExpoPushTokenView(generics.GenericAPIView):
    serializer_class = ExpoPushTokenSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(request=ExpoPushTokenSerializer, responses=ExpoPushTokenSerializer)
    def post(self, request):
        token = (request.data.get('token') or '').strip()
        if not token:
            return Response({'error': 'token requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        plataforma = request.data.get('plataforma')
        obj, _ = ExpoPushToken.objects.update_or_create(
            token=token,
            defaults={'usuario': request.user, 'plataforma': plataforma},
        )
        return Response(self.get_serializer(obj).data, status=status.HTTP_200_OK)

    def delete(self, request):
        token = (request.data.get('token') or '').strip()
        if not token:
            return Response({'error': 'token requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        ExpoPushToken.objects.filter(token=token, usuario=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
