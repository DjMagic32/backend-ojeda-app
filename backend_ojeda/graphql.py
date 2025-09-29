from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed


class JWTGraphQLView(GraphQLView):
    """GraphQL view that authenticates requests via Simple JWT tokens."""

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
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
