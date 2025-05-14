from django.urls import path, include
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r'discounts', views.DiscountViewSet)

urlpatterns = [
    path('', include(router.urls)),
]