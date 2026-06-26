from django.urls import path, include
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r'categories', views.CategoryViewSet)
router.register(r'subcategories', views.SubcategoryViewSet)
router.register(r'product-images', views.ProductImageViewSet)
router.register(r'tags', views.TagViewSet)
router.register(r'', views.ProductViewSet, basename='product')

urlpatterns = [
    path('relevant-tags/', views.RelevantTagsView.as_view(), name='relevant-tags-list'),
    path('relevant-brands/', views.RelevantBrandsView.as_view(), name='relevant-brands-list'),
    path('', include(router.urls)),
]