from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from store.serializers import UsuarioSerializer

from graphene_django.views import GraphQLView
from rest_framework.request import Request as DRFRequest
from rest_framework.settings import api_settings
from rest_framework.exceptions import AuthenticationFailed
from django.http import JsonResponse
import json # Though not used in this version of dispatch

# For CustomTokenObtainPairSerializer
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims if needed
        # token['username'] = user.username
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Add user data to the response
        # Ensure self.user is available after super().validate()
        if hasattr(self, 'user') and self.user:
             data['user'] = UsuarioSerializer(self.user).data
        return data

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# For GraphQL Authentication with DRF JWT
class DRFAuthenticatedGraphQLView(GraphQLView):
    def dispatch(self, request, *args, **kwargs):
        # Create a DRF Request to trigger DRF's authentication mechanisms
        # This will populate drf_request_obj.user if JWT is valid and provided
        # Instantiate authenticator classes
        auth_classes = getattr(api_settings, 'DEFAULT_AUTHENTICATION_CLASSES', [])
        authenticators = [auth() for auth in auth_classes]
        print(f"DRFAuthenticatedGraphQLView: Authenticators: {authenticators}")


        drf_request_obj = DRFRequest(
            request,
            # parsers are not strictly needed for auth, but good practice if body is read by DRF
            parsers=getattr(api_settings, 'DEFAULT_PARSER_CLASSES', []),
            authenticators=authenticators, # Pass instantiated authenticators
            negotiator=getattr(api_settings, 'DEFAULT_CONTENT_NEGOTIATION_CLASS', None), # Not strictly for auth
            parser_context={}
        )

        # If DRF authentication populates user on its request wrapper,
        # copy it to the original Django request so Graphene's info.context.request.user is set.
        print(f"DRFAuthenticatedGraphQLView: Original request.user before DRF auth: {getattr(request, 'user', 'N/A')}")
        print(f"DRFAuthenticatedGraphQLView: HTTP_AUTHORIZATION header: {request.META.get('HTTP_AUTHORIZATION')}") # Check header
        if hasattr(drf_request_obj, 'user') and drf_request_obj.user: # Check if user attribute exists
            print(f"DRFAuthenticatedGraphQLView: drf_request_obj.user is: {drf_request_obj.user}, authenticated: {drf_request_obj.user.is_authenticated}")
            if drf_request_obj.user.is_authenticated:
                request.user = drf_request_obj.user
                if hasattr(drf_request_obj, 'auth'): # Also copy token if available
                    request.auth = drf_request_obj.auth
                print(f"DRFAuthenticatedGraphQLView: Django request.user set to: {request.user}")
            else:
                print(f"DRFAuthenticatedGraphQLView: drf_request_obj.user is Anonymous or not authenticated.")
        else:
            print(f"DRFAuthenticatedGraphQLView: drf_request_obj has no user attribute or it's None after auth attempt.")

        # Handle potential AuthenticationFailed raised by DRF authenticators
        # This ensures that if JWT validation fails (e.g. expired, invalid),
        # we return a GraphQL-like error response instead of DRF's default HTML/JSON error response
        # or letting the exception propagate raw.
        try:
            # The actual authentication happens when request.user or request.authenticators is accessed by DRF.
            # Forcing access here if not already done by creating DRFRequest with authenticators.
            # This access will trigger the authentication process on drf_request_obj
            _ = drf_request_obj.user
            # If authentication was successful, drf_request_obj.user is now populated.
            # We've already copied it to the Django request object 'request.user'.

        except AuthenticationFailed as e:
            # Format the DRF AuthenticationFailed error into a GraphQL error structure.
            # Graphene's format_error is a staticmethod.
            formatted_error = GraphQLView.format_error(e)
            error_payload = {"errors": [formatted_error]}
            return JsonResponse(error_payload, status=401) # Standard unauthorized status
        # Removed the explicit TypeError catch for JWTAuthentication.authenticate,
        # as accessing _drf_request.user is the standard way to trigger authentication.
        # If a TypeError still occurs there, it's a deeper issue with DRF/JWT setup.

        return super().dispatch(request, *args, **kwargs)

    # Graphene-Django's GraphQLView by default puts the original Django request
    # into info.context (as info.context.request).
    # The `resolve_me` resolver uses `info.context.user`.
    # Django's AuthenticationMiddleware sets `request.user` based on session or auth backends.
    # By updating `request.user` in dispatch (as done above), `info.context.user` should reflect
    # the JWT authenticated user.
    # So, `get_context` override might not be strictly necessary if `request.user` is correctly populated before super().dispatch.
    # The default get_context is: `return {'request': request}`.
    # Then Graphene provides `info.context.request.user`.
    # If our dispatch correctly sets `request.user`, then `info.context.request.user` will be correct.
    # And `info.context.user` (shortcut) should also work.

    # Note: Ensure this custom view is used in urls.py for the /graphql endpoint.
