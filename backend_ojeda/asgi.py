"""ASGI config para backend_ojeda con soporte de Django Channels.

HTTP sigue siendo manejado por Django; WebSocket pasa por el router
de ``store.routing`` y autentica vía JWT en query param o header.
"""

import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_ojeda.settings')
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from django.core.asgi import get_asgi_application  # noqa: E402

from store.middleware.jwt_auth import JWTAuthMiddlewareStack  # noqa: E402
from store.routing import websocket_urlpatterns  # noqa: E402

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        'http': django_asgi_app,
        'websocket': JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
