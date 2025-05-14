from django.contrib import admin
from django.urls import path, include

from rest_framework.schemas import get_schema_view

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenBlacklistView,
)
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include('accounts.urls')),
    path('api/products/', include('products.urls')),
    path('api/inventory/', include('inventory.urls')),
    path('api/carts/', include('carts.urls')),
    path('api/sales/', include('sales.urls')),
    
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # Login: Obtiene token de acceso y refresco
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/logout/', TokenBlacklistView.as_view(), name='token_blacklist'),
    # path('api-auth/', include('rest_framework.urls')),
# Genera el schema OpenAPI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # UI de Swagger:
    path('api/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # UI de Redoc:
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]