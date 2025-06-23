from django.urls import path, include
# from rest_framework.routers import DefaultRouter # Replaced by NestedDefaultRouter
from rest_framework_nested.routers import DefaultRouter, NestedDefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    UsuarioViewSet, TiendaViewSet, ProductoTiendaViewSet, CarritoView, PedidoView,
    CategoriaViewSet, ProductoViewSet, ComentarioViewSet, ComentarioProductoViewSet,
    ReferenciaViewSet, WalletViewSet, WalletActionView, CreateUserView, UsuarioDetalleView,
    GoogleLogin, AppleLogin, StripeCreatePaymentIntentView, # stripe_webhook is imported directly
    BinanceCreateOrderView, # binance_webhook is imported directly
    ChatRoomViewSet, ChatMessageViewSet # Added Chat ViewSets
)
from .views import stripe_webhook, binance_webhook # Import webhooks directly

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet)
router.register(r'tiendas', TiendaViewSet)
router.register(r'productos-tienda', ProductoTiendaViewSet)
router.register(r'categorias', CategoriaViewSet)
router.register(r'productos', ProductoViewSet)
router.register(r'comentarios', ComentarioViewSet)
router.register(r'comentarios-producto', ComentarioProductoViewSet)
router.register(r'referencias', ReferenciaViewSet)
router.register(r'wallets', WalletViewSet)
router.register(r'chat_rooms', ChatRoomViewSet, basename='chatroom')

# Nested router for messages within a chat room
# Generates URLs like: /api/store/app/chat_rooms/{room_pk}/messages/
chat_rooms_router = NestedDefaultRouter(router, r'chat_rooms', lookup='room')
chat_rooms_router.register(r'messages', ChatMessageViewSet, basename='chatroom-messages')

urlpatterns = [
    path('app/', include(router.urls)),
    path('app/', include(chat_rooms_router.urls)), # Include nested chat message routes
    path('register-user/', CreateUserView.as_view(), name='user-register'),  # Ruta para crear usuarios
    path('carrito/', CarritoView.as_view(), name='carrito'),
    path('pedidos/', PedidoView.as_view(), name='pedidos'),
    path('wallet-action/', WalletActionView.as_view(), name='wallet-action'),
    path('usuario-detalle/', UsuarioDetalleView.as_view(), name='usuario-detalle'),
    path('auth/google/', GoogleLogin.as_view(), name='google_login'),
    path('auth/apple/', AppleLogin.as_view(), name='apple_login'),
    path('stripe/create-payment-intent/', StripeCreatePaymentIntentView.as_view(), name='stripe-create-payment-intent'),
    path('stripe/webhook/', stripe_webhook, name='stripe-webhook'),
    path('binance/create-order/', BinanceCreateOrderView.as_view(), name='binance-create-order'),
    path('binance/webhook/', binance_webhook, name='binance-webhook'),
]