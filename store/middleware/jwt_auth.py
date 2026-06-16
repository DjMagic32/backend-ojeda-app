"""Middleware ASGI que autentica conexiones WebSocket usando SimpleJWT.

Soporta tomar el token desde:
- query string ``?token=...`` (recomendado para clientes WS donde no se
  pueden enviar headers cómodamente desde React Native)
- header ``Authorization: Bearer ...`` cuando esté disponible

Si la validación falla, ``scope['user']`` queda como ``AnonymousUser``.
"""

from __future__ import annotations

from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _get_user(validated_token):
    from rest_framework_simplejwt.authentication import JWTAuthentication

    try:
        return JWTAuthentication().get_user(validated_token)
    except Exception:  # noqa: BLE001
        return AnonymousUser()


def _extract_token(scope) -> str | None:
    query = parse_qs((scope.get('query_string') or b'').decode())
    token = query.get('token') or query.get('access_token')
    if token:
        return token[0]
    for header_name, header_value in scope.get('headers', []):
        if header_name == b'authorization':
            value = header_value.decode()
            if value.lower().startswith('bearer '):
                return value.split(' ', 1)[1].strip()
    return None


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

        token = _extract_token(scope)
        scope = dict(scope)
        scope['user'] = AnonymousUser()
        if token:
            try:
                validated = JWTAuthentication().get_validated_token(token)
                scope['user'] = await _get_user(validated)
            except (InvalidToken, TokenError):
                pass
        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """Aplica JWT primero y, como fallback, sesiones Django."""
    return JWTAuthMiddleware(AuthMiddlewareStack(inner))
