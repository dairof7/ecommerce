from django.urls import path, include
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r'carts', views.CartViewSet, basename='cart')
router.register(r'quotes', views.QuoteViewSet, basename='quote')

urlpatterns = [
    path('', include(router.urls)),
]
