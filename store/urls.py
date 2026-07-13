from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    UsuarioViewSet,
    TiendaViewSet,
    ProductoTiendaViewSet,
    CarritoView,
    ConversationViewSet,
    ExpoPushTokenView,
    PedidoView,
    CategoriaViewSet,
    ProductoViewSet,
    ComentarioViewSet,
    ComentarioProductoViewSet,
    ReferenciaViewSet,
    StoreDashboardView,
    TasaCambioHistoryView,
    TasaCambioView,
    WalletViewSet,
    WalletActionView,
    CreateUserView,
    DriverDocumentosView,
    EmailDisponibleView,
    UsuarioDetalleView,
    UsuarioProfileUpdateView,
    StoreOrderViewSet,
    MiTiendaView,
    ProductoFavoritoView,
    NotificacionListView,
    NotificacionMarkReadView,
    NotificacionUnreadCountView,
    ReporteCreateView,
    VentaPresencialCreateView,
    ArticuloUsadoViewSet,
)

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet)
router.register(r'tiendas', TiendaViewSet)
router.register(r'productos-tienda', ProductoTiendaViewSet)
router.register(r'store-orders', StoreOrderViewSet, basename='store-orders')
router.register(r'categorias', CategoriaViewSet)
router.register(r'productos', ProductoViewSet)
router.register(r'comentarios', ComentarioViewSet)
router.register(r'comentarios-producto', ComentarioProductoViewSet)
router.register(r'referencias', ReferenciaViewSet)
router.register(r'wallets', WalletViewSet)
router.register(r'conversations', ConversationViewSet, basename='conversations')
router.register(r'articulos-usados', ArticuloUsadoViewSet, basename='articulos-usados')

urlpatterns = [
    path('', include(router.urls)),
    path('register-user/', CreateUserView.as_view(), name='user-register'),  # Ruta para crear usuarios
    path('email-disponible/', EmailDisponibleView.as_view(), name='email-disponible'),
    path('driver-documentos/', DriverDocumentosView.as_view(), name='driver-documentos'),
    path('carrito/', CarritoView.as_view(), name='carrito'),
    path('pedidos/', PedidoView.as_view(), name='pedidos'),
    path('wallet-action/', WalletActionView.as_view(), name='wallet-action'),
    path('usuario-detalle/', UsuarioDetalleView.as_view(), name='usuario-detalle'),
    path('usuario-perfil/', UsuarioProfileUpdateView.as_view(), name='usuario-perfil'),
    path('mi-tienda/', MiTiendaView.as_view(), name='mi-tienda'),
    path('favoritos/', ProductoFavoritoView.as_view(), name='favoritos'),
    path('notificaciones/', NotificacionListView.as_view(), name='notificaciones'),
    path('notificaciones/unread-count/', NotificacionUnreadCountView.as_view(), name='notificaciones-unread-count'),
    path('notificaciones/<int:pk>/read/', NotificacionMarkReadView.as_view(), name='notificacion-marcar-leida'),
    path('push-tokens/', ExpoPushTokenView.as_view(), name='push-tokens'),
    path('exchange-rate/', TasaCambioView.as_view(), name='exchange-rate'),
    path('exchange-rate/history/', TasaCambioHistoryView.as_view(), name='exchange-rate-history'),
    path('store/dashboard/', StoreDashboardView.as_view(), name='store-dashboard'),
    path('reportes/', ReporteCreateView.as_view(), name='reportes'),
    path('ventas-presenciales/', VentaPresencialCreateView.as_view(), name='ventas-presenciales'),
]
