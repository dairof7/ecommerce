# site_settings/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BannerViewSet

router = DefaultRouter()
router.register(r'banners', BannerViewSet, basename='banner')

urlpatterns = [
    path('', include(router.urls)),
]

# En tu urls.py principal del proyecto:
# path('api/site-settings/', include('site_settings.urls')),