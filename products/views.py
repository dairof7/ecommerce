from rest_framework import viewsets, generics, filters, permissions
from .models import Category, Subcategory, Product, ProductImage, Tag
from .serializers import CategorySerializer, SubcategorySerializer, ProductSerializer, ProductImageSerializer, TagSerializer
from django_filters.rest_framework import DjangoFilterBackend

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    
    search_fields = ['name'] # Puedes añadir búsqueda por nombre si quieres
    ordering_fields = ['name', 'category__name'] # Permite ordenar por nombre o nombre de categoría


class SubcategoryViewSet(viewsets.ModelViewSet):
    queryset = Subcategory.objects.all().order_by('name')
    serializer_class = SubcategorySerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    
    search_fields = ['name'] # Puedes añadir búsqueda por nombre si quieres
    ordering_fields = ['name', 'category__name'] # Permite ordenar por nombre o nombre de categoría
    filterset_fields = ['category'] # Especifica el campo por el que quieres filtrar

class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer

# class ProductViewSet(viewsets.ModelViewSet):
#     queryset = Product.objects.all()
#     serializer_class = ProductSerializer
#     filter_backends = [filters.SearchFilter, filters.OrderingFilter]
#     search_fields = ['name', 'description', 'category__name', 'subcategory__name', 'tags__name']
#     ordering_fields = ['name', 'sale_price']

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('id')
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    search_fields = ['name', 'description', 'category__name', 'subcategory__name', 'tags__name']
    ordering_fields = ['name', 'sale_price']
    filterset_fields = ['category', 'subcategory']
    
    # permission_classes = [permissions.IsAdminUser] # Descomentar si quieres que solo los administradores puedan acceder a esta vista
    
        # --- AÑADIR CLASES DE PERMISOS AQUÍ ---
    def get_permissions(self):
        """
        Instancia y retorna la lista de permisos que esta vista requiere.
        """
        if self.action in ['list', 'retrieve']:
            # Permitir a cualquiera ver la lista y los detalles de los productos
            permission_classes = [permissions.AllowAny]
        else:
            # Requerir que el usuario sea administrador para crear, actualizar, eliminar
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]

class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer