from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import UsuarioViewSet, TiendaViewSet, ProductoTiendaViewSet, CarritoView, PedidoView, CategoriaViewSet, ProductoViewSet, ComentarioViewSet, ComentarioProductoViewSet, ReferenciaViewSet, WalletViewSet, WalletActionView, CreateUserView, UsuarioDetalleView

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

urlpatterns = [
    path('app/', include(router.urls)),
    path('register-user/', CreateUserView.as_view(), name='user-register'),  # Ruta para crear usuarios
    path('carrito/', CarritoView.as_view(), name='carrito'),
    path('pedidos/', PedidoView.as_view(), name='pedidos'),
    path('wallet-action/', WalletActionView.as_view(), name='wallet-action'),
    path('usuario-detalle/', UsuarioDetalleView.as_view(), name='usuario-detalle'),
]