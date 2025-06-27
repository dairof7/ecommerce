from rest_framework import viewsets, generics, filters, permissions
from .models import Category, Subcategory, Product, ProductImage, Tag
from .serializers import CategorySerializer, SubcategorySerializer, ProductSerializer, ProductImageSerializer, TagSerializer, RelevantTagSerializer
from django_filters.rest_framework import DjangoFilterBackend
from .filters import ProductFilter
from django.db.models import Count, Q
from rest_framework import views, response

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    
    search_fields = ['name'] # Puedes añadir búsqueda por nombre si quieres
    ordering_fields = ['name', 'display_order', 'category__name'] # Permite ordenar por nombre o nombre de categoría


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
    queryset = Product.objects.all().order_by('-is_featured', '-discount', '-created_at') # Ordenar por destacados primero y luego por fecha de creación
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    search_fields = ['name', 'description', 'category__name', 'subcategory__name', 'tags__name']
    ordering_fields = ['name', 'sale_price', 'created_at']
    # con este busco por el nombre de la categoría y subcategoría
    filterset_class = ProductFilter
    # filterset_fields = ['category', 'subcategory', 'tags']

    # permission_classes = [permissions.IsAdminUser] # Descomentar si quieres que solo los administradores puedan acceder a esta vista
        # --- AÑADIR CLASES DE PERMISOS AQUÍ ---
    def get_permissions(self):
        """
        Instancia y retorna la lista de permisos que esta vista requiere.
        """
        if self.action in ['list', 'retrieve', 'featured_products', 'bestselling_products']:
            # Permitir a cualquiera ver la lista y los detalles de los productos
            permission_classes = [permissions.AllowAny]
        else:
            # Requerir que el usuario sea administrador para crear, actualizar, eliminar
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]
    
    from rest_framework.decorators import action
    from rest_framework.response import Response
    @action(detail=False, methods=['get'], url_path='featured')
    def featured_products(self, request):
        """
        Retorna una lista de productos marcados como destacados (is_featured=True).
        """
        # Obtener el queryset base del ViewSet para reutilizar filtros y anotaciones si los hubiera
        base_queryset = self.get_queryset() 
        featured_qs = base_queryset.filter(is_featured=True).order_by('?') # Orden aleatorio o por '-created_at', etc.
        
        limit_str = request.query_params.get('limit', None)
        if limit_str and limit_str.isdigit():
            limit = int(limit_str)
            featured_qs = featured_qs[:limit] # Aplicar el límite

        page = self.paginate_queryset(featured_qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(featured_qs, many=True)
        return Response(serializer.data)


    @action(detail=False, methods=['get'], url_path='bestsellers')
    def bestselling_products(self, request):
        """
        Placeholder para los más vendidos. Por ahora, devuelve productos destacados.
        Permite un parámetro ?limit=N.
        """
        base_queryset = self.get_queryset()
        # En una implementación real, aquí filtrarías y ordenarías por conteo de ventas.
        # Por ahora, usamos is_featured como un proxy o simplemente un orden aleatorio/reciente.
        bestsellers_qs = base_queryset.filter(is_featured=True).order_by('-created_at') # Ejemplo: destacados más recientes

        limit_str = request.query_params.get('limit', None)
        if limit_str and limit_str.isdigit():
            limit = int(limit_str)
            bestsellers_qs = bestsellers_qs[:limit]

        page = self.paginate_queryset(bestsellers_qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(bestsellers_qs, many=True)
        return Response(serializer.data)

class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    











class RelevantTagsView(views.APIView):
    permission_classes = [permissions.AllowAny] # Los tags relevantes suelen ser públicos

    def get(self, request, *args, **kwargs):
        # 1. Obtener los productos que coinciden con los filtros actuales
        #    (categoría, subcategoría, búsqueda, etc., PERO NO los tags seleccionados)
        
        # Usamos ProductFilter para aplicar los filtros primarios
        # Creamos una instancia del ProductFilter con los datos del request
        # y el queryset base de todos los productos.
        product_queryset = Product.objects.all() # Empezar con todos los productos
        
        # Preparamos los datos de filtrado para ProductFilter, excluyendo 'tags' o 'tags_name'
        # para no filtrar por tags que el usuario ya haya podido seleccionar
        # ya que queremos mostrar todos los tags relevantes a los *otros* filtros.
        # Si el frontend envía los tags seleccionados para *excluirlos* de esta lista,
        # la lógica sería diferente (ej. para mostrar "Refinar por otros tags").
        # Por ahora, asumimos que este endpoint se llama con los filtros *antes* de seleccionar un tag.
        
        # Copiamos los query_params para no modificar el original del request
        # y poder eliminar los filtros de tags si vinieran.
        # Sin embargo, este endpoint NO debería recibir filtros de tags si su propósito
        # es mostrar los tags disponibles para el filtrado actual.
        
        filtering_params = request.query_params.copy()
        # Eliminar parámetros de tags si existieran, ya que queremos los tags disponibles
        # basados en los *otros* filtros.
        # Esto es si el mismo frontend usa los mismos query params para esta llamada.
        filtering_params.pop('tags', None)
        filtering_params.pop('tags_name', None)
        # if 'search' in filtering_params:
        #     filtering_params['name'] = filtering_params['search']
        
        # Aplicar los filtros de producto (categoría, subcategoría, búsqueda, etc.)
        # utilizando tu ProductFilter existente.
        product_filter = ProductFilter(data=filtering_params, queryset=product_queryset, request=request)
        filtered_products_qs = product_filter.qs # Este es el queryset de productos ya filtrados
        # 2. A partir de estos productos filtrados, obtener los tags y su conteo
        # Usamos annotate para contar cuántos productos filtrados tiene cada tag.
        # distinct=True en Count es importante si un producto puede tener el mismo tag múltiples veces
        # (lo cual no debería pasar con ManyToManyField por defecto).
        relevant_tags_qs = Tag.objects.filter(
            product__in=filtered_products_qs # Solo tags de los productos que pasaron los filtros primarios
        ).annotate(
            product_count=Count('product', filter=Q(product__in=filtered_products_qs)) # Contar productos DENTRO del queryset filtrado
        ).filter(
            product_count__gt=0 # Solo tags que realmente tienen productos en la selección actual
        ).order_by('-product_count', 'name').distinct() # Ordenar por popularidad y luego nombre

        # Serializar los resultados
        serializer = RelevantTagSerializer(relevant_tags_qs, many=True)
        return response.Response(serializer.data)

# Opcional: Si prefieres un ViewSet para consistencia (aunque solo tenga 'list')
# class RelevantTagsViewSet(viewsets.ReadOnlyModelViewSet):
#     serializer_class = RelevantTagSerializer
#     permission_classes = [permissions.AllowAny]
#     filter_backends = [] # No usamos los filter_backends estándar aquí

#     def get_queryset(self):
#         # Lógica similar a la de RelevantTagsView.get() para construir el queryset
#         # ...
#         product_queryset = Product.objects.all()
#         product_filter = ProductFilter(data=self.request.query_params, queryset=product_queryset, request=self.request)
#         filtered_products_qs = product_filter.qs
        
#         relevant_tags_qs = Tag.objects.filter(
#             product__in=filtered_products_qs
#         ).annotate(
#             product_count=Count('product', filter=Q(product__in=filtered_products_qs))
#         ).filter(
#             product_count__gt=0
#         ).order_by('-product_count', 'name').distinct()
#         return relevant_tags_qs