from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from django.views.generic import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from .views import CustomTokenObtainPairView, CustomTokenRefreshView
from .graphql import JWTGraphQLView
from .schema import schema



from rest_framework.permissions import AllowAny, IsAdminUser


def api_root(request):
    """Health-friendly API landing page without exposing interactive tooling."""
    return JsonResponse({
        'service': 'TuPlaza API',
        'status': 'ok',
        'docs': '/docs/' if settings.SERVE_API_DOCS else None,
    })

urlpatterns = [
    path('', api_root, name='api-root'),
    path('admin/', admin.site.urls),
    path('api/store/', include('store.urls')),  # Aquí asegúrate de que la ruta sea correcta
    # JWT token endpoints
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('api/graphql/', JWTGraphQLView.as_view(schema=schema), name='graphql'),
]

if settings.SERVE_API_DOCS:
    docs_permissions = [AllowAny] if settings.DEBUG else [IsAdminUser]
    urlpatterns += [
        path(
            'api/schema/',
            SpectacularAPIView.as_view(permission_classes=docs_permissions),
            name='schema',
        ),
        path(
            'docs/',
            SpectacularSwaggerView.as_view(
                url_name='schema',
                permission_classes=docs_permissions,
            ),
            name='swagger-ui',
        ),
        path(
            'redoc/',
            SpectacularRedocView.as_view(
                url_name='schema',
                permission_classes=docs_permissions,
            ),
            name='redoc',
        ),
        # Alias legados
        path('swagger/', RedirectView.as_view(pattern_name='swagger-ui', permanent=False)),
        path('schema/', RedirectView.as_view(pattern_name='schema', permanent=False)),
    ]

if (settings.DEBUG or settings.SERVE_MEDIA) and not settings.S3_MEDIA_ENABLED:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
