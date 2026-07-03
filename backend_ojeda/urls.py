from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from .views import CustomTokenObtainPairView
from .graphql import JWTGraphQLView
from .schema import schema



from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='swagger-ui', permanent=False)),
    path('admin/', admin.site.urls),
    path('api/store/', include('store.urls')),  # Aquí asegúrate de que la ruta sea correcta
    # JWT token endpoints
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    # Alias legados
    path('swagger/', RedirectView.as_view(pattern_name='swagger-ui', permanent=False)),
    path('schema/', RedirectView.as_view(pattern_name='schema', permanent=False)),
    path('api/graphql/', JWTGraphQLView.as_view(schema=schema), name='graphql'),
]

if settings.DEBUG or settings.SERVE_MEDIA:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
