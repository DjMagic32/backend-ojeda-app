import json

from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.models import AnonymousUser
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed


class JWTGraphQLView(GraphQLView):
    """GraphQL view that authenticates requests via Simple JWT tokens."""

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        client_ip = self._client_ip(request)
        if self._is_rate_limited(
            f'graphql:ip:{client_ip}',
            settings.GRAPHQL_RATE_LIMIT,
        ):
            return JsonResponse(
                {'error': 'Demasiadas solicitudes. Intenta de nuevo en un momento.'},
                status=429,
                headers={'Retry-After': '60'},
            )

        operation_name = self._operation_name(request)
        if operation_name in self.auth_operations and self._is_rate_limited(
            f'graphql:auth:{client_ip}',
            settings.GRAPHQL_AUTH_RATE_LIMIT,
        ):
            return JsonResponse(
                {'error': 'Demasiados intentos de autenticación. Intenta de nuevo más tarde.'},
                status=429,
                headers={'Retry-After': '60'},
            )

        return self._dispatch_authenticated(request, *args, **kwargs)

    auth_operations = {
        'login',
        'googlelogin',
        'requestpasswordresetcode',
        'resetpassword',
    }

    @staticmethod
    def _client_ip(request):
        # Railway/proxy debe sobrescribir X-Forwarded-For. Tomamos la primera
        # IP para no compartir el límite entre todos los usuarios del proxy.
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
        return (forwarded_for.split(',')[0].strip() or request.META.get('REMOTE_ADDR', 'unknown'))

    @staticmethod
    def _is_rate_limited(key, limit):
        try:
            current = cache.incr(key)
        except ValueError:
            cache.add(key, 1, timeout=60)
            current = 1
        return current > max(1, int(limit))

    @staticmethod
    def _operation_name(request):
        try:
            if request.method == 'GET':
                raw_body = request.GET.get('query', '')
                operation_name = request.GET.get('operationName', '')
            else:
                raw_body = request.body.decode('utf-8')
                payload = json.loads(raw_body or '{}')
                if isinstance(payload, list):
                    payload = payload[0] if payload else {}
                operation_name = payload.get('operationName', '') if isinstance(payload, dict) else ''
                if operation_name:
                    return operation_name.replace('_', '').lower()

            # Fallback para clientes que no envían operationName: sólo
            # identificamos operaciones de autenticación por su nombre.
            normalized = ''.join(str(raw_body).split()).lower()
            for candidate in JWTGraphQLView.auth_operations:
                if candidate in normalized:
                    return candidate
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError, TypeError):
            return ''
        return ''

    def _dispatch_authenticated(self, request, *args, **kwargs):
        authenticator = JWTAuthentication()
        try:
            header = authenticator.get_header(request)
            if header is not None:
                raw_token = authenticator.get_raw_token(header)
                validated_token = authenticator.get_validated_token(raw_token)
                request.user = authenticator.get_user(validated_token)
                request.auth = validated_token
            elif not hasattr(request, "user"):
                request.user = AnonymousUser()
        except (AuthenticationFailed, Exception):
            request.user = AnonymousUser()
            request.auth = None
        return super().dispatch(request, *args, **kwargs)

    @classmethod
    def as_view(cls, **initkwargs):  # type: ignore[override]
        initkwargs.setdefault("graphiql", settings.DEBUG)
        return super().as_view(**initkwargs)
