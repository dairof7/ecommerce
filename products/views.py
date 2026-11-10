from rest_framework import viewsets, generics, filters, permissions
from .models import Category, Subcategory, Product, ProductImage, Tag, Brand, Supplier
from .serializers import (
    CategorySerializer, SubcategorySerializer, ProductSerializer, 
    ProductImageSerializer, TagSerializer, RelevantTagSerializer, 
    RelevantBrandSerializer, BrandSerializer, SupplierSerializer
)
from django_filters.rest_framework import DjangoFilterBackend
from .filters import ProductFilter
from django.db.models import Count, Q, Sum
from rest_framework import views, response
from rest_framework.response import Response
from django.db.models import Case, When, Value, IntegerField
from carts.models import QuoteItem
from decimal import Decimal
from django.db import transaction
from inventory.models import StockEntry

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    
    search_fields = ['name'] # Puedes añadir búsqueda por nombre si quieres
    ordering_fields = ['name', 'display_order', 'category__name'] # Permite ordenar por nombre o nombre de categoría


class SubcategoryViewSet(viewsets.ModelViewSet):
    queryset = Subcategory.objects.filter(is_active=True).order_by('name')
    serializer_class = SubcategorySerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    
    search_fields = ['name'] # Puedes añadir búsqueda por nombre si quieres
    ordering_fields = ['name', 'category__name'] # Permite ordenar por nombre o nombre de categoría
    filterset_fields = ['category'] # Especifica el campo por el que quieres filtrar


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all().order_by('name')
    serializer_class = TagSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']
    pagination_class = None

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all().order_by('name')
    serializer_class = BrandSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']
    pagination_class = None

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all().order_by('name')
    serializer_class = SupplierSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']
    pagination_class = None

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    search_fields = ['name', 'description', 'category__name', 'subcategory__name', 'tags__name', 'brand__name']
    ordering_fields = ['name', 'sale_price', 'purchase_price', 'created_at', 'stock', 'incoming_stock', 'discount']
    # con este busco por el nombre de la categoría y subcategoría
    filterset_class = ProductFilter
    # filterset_fields = ['category', 'subcategory', 'tags']

    def get_queryset(self):
        """
        - Usuarios normales: Ven solo productos activos que NO son servicios.
        - Administradores (staff): Ven TODOS los productos, para poder usarlos en el POS.
        """
        base_queryset = Product.objects.all()

        # Si el usuario no es administrador, aplicamos filtros de visibilidad estrictos.
        if not self.request.user.is_staff:
            base_queryset = base_queryset.filter(
                is_active=True, 
                is_service=False, # Oculta los servicios a los clientes
                category__is_active=True, 
                subcategory__is_active=True
            )

        # Anotación y ordenamiento para todos
        queryset = base_queryset.annotate(
            availability_status=Case(
                When(stock__gt=0, then=Value(0)),                      # Prioridad 0: En stock
                When(stock=0, incoming_stock__gt=0, then=Value(1)),    # Prioridad 1: Llegará pronto
                default=Value(2),                                      # Prioridad 2: Totalmente agotado
                output_field=IntegerField(),
            )
        ).order_by('availability_status', '-is_featured', '-discount', '-created_at')
        return queryset

    # permission_classes = [permissions.IsAdminUser] # Descomentar si quieres que solo los administradores puedan acceder a esta vista
        # --- AÑADIR CLASES DE PERMISOS AQUÍ ---
    def get_permissions(self):
        """
        Instancia y retorna la lista de permisos que esta vista requiere.
        """
        if self.action in ['list', 'retrieve', 'featured_products', 'bestselling_products', 'new_products']:
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

    @action(detail=False, methods=['get'], url_path='new-arrivals')
    def new_products(self, request):
        """
        Retorna una lista de productos nuevos.
        """
        # Usamos el queryset base pero garantizamos que sean activos y no servicios.
        # Excluimos subcategorías de consumibles/accesorios en lugar de filtrar por precio.
        excluded_subcats = ["ACCESORIOS CAMARAS", "ACCESORIOS COMPUTACIÓN", "MEMORIA USB", "MICRO SD"]
        base_queryset = self.get_queryset().filter(
            is_active=True, 
            is_service=False,
            sale_price__gt=45000
        ).exclude(
            subcategory__name__in=excluded_subcats
        )
        new_qs = base_queryset.filter(stock__gt=0).order_by('-created_at')
        limit_str = request.query_params.get('limit', None)
        if limit_str and limit_str.isdigit():
            limit = int(limit_str)
            new_qs = new_qs[:limit] # Aplicar el límite

        page = self.paginate_queryset(new_qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(new_qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='bestsellers')
    def bestselling_products(self, request):
        """
        Retorna los productos más vendidos, basado en la cantidad vendida en cotizaciones 'paid'.
        Permite un parámetro ?limit=N.
        """
        # 1. Obtener los IDs de productos y su cantidad total vendida de cotizaciones pagadas
        sold_products_data = QuoteItem.objects.filter(
            quote__status='paid'
        ).values(
            'product_id'
        ).annotate(
            total_sold=Sum('quantity')
        ).order_by('-total_sold')
        # 2. Extraer la lista ordenada de IDs de productos
        ordered_product_ids = [item['product_id'] for item in sold_products_data]

        # Si no hay productos vendidos, devolver una lista vacía
        if not ordered_product_ids:
            return Response([])

        # 3. Obtener los objetos Product respetando los filtros (activos, no servicios)
        # y excluyendo las subcategorías de repuestos/consumibles para dar espacio a productos reales de bajo costo.
        excluded_subcats = ["ACCESORIOS CAMARAS", "ACCESORIOS COMPUTACIÓN", "MEMORIA USB", "MICRO SD"]
        base_queryset = self.get_queryset().filter(
            is_active=True, 
            is_service=False,
            sale_price__gt=45000,
        ).exclude(
            subcategory__name__in=excluded_subcats
        )
        
        preserved_order = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(ordered_product_ids)])
        bestsellers_qs = base_queryset.filter(pk__in=ordered_product_ids).order_by(preserved_order)

        # Aplicar el límite si se proporciona
        limit_str = request.query_params.get('limit', None)
        if limit_str and limit_str.isdigit():
            limit = int(limit_str)
            bestsellers_qs = bestsellers_qs[:limit]

        # Paginar los resultados
        page = self.paginate_queryset(bestsellers_qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(bestsellers_qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='receive-stock')
    def receive_stock(self, request, pk=None):
        """
        Recibe stock en tránsito para un producto específico (total o parcial).
        Crea una StockEntry que actualiza el stock físico y recalcula el costo promedio.
        """
        product = self.get_object()
        
        try:
            quantity = int(request.data.get('quantity', product.incoming_stock))
        except (ValueError, TypeError):
            return Response({'error': 'La cantidad debe ser un número entero válido.'}, status=400)
            
        if quantity <= 0:
            return Response({'error': 'La cantidad a recibir debe ser mayor a 0.'}, status=400)
            
        if quantity > product.incoming_stock:
            return Response({
                'error': f'La cantidad a recibir ({quantity}) supera el stock en tránsito ({product.incoming_stock}).'
            }, status=400)
            
        purchase_price = request.data.get('purchase_price')
        if purchase_price is not None:
            try:
                purchase_price = Decimal(str(purchase_price))
            except Exception:
                purchase_price = product.purchase_price or Decimal('0.00')
        else:
            purchase_price = product.purchase_price or Decimal('0.00')
            
        notes = request.data.get('notes', 'Recepción de stock en tránsito desde Frontend')
        
        with transaction.atomic():
            product.incoming_stock -= quantity
            product.save(update_fields=['incoming_stock'])
            
            StockEntry.objects.create(
                product=product,
                quantity=quantity,
                purchase_price=purchase_price,
                notes=notes
            )
            
        product.refresh_from_db()
        return Response({
            'message': f'Se recibieron {quantity} unidades de "{product.name}" en bodega exitosamente.',
            'product_id': product.id,
            'name': product.name,
            'new_stock': product.stock,
            'remaining_incoming': product.incoming_stock,
            'average_cost': product.average_cost
        })

    @action(detail=False, methods=['post'], url_path='receive-multiple-stock')
    def receive_multiple_stock(self, request):
        """
        Recibe stock en tránsito de múltiples productos en lote.
        """
        items = request.data.get('items', [])
        if not items or not isinstance(items, list):
            return Response({'error': 'Se requiere una lista de productos en el campo "items".'}, status=400)
            
        received_products = []
        errors = []
        
        with transaction.atomic():
            for item in items:
                product_id = item.get('product_id')
                try:
                    product = Product.objects.select_for_update().get(pk=product_id)
                except Product.DoesNotExist:
                    errors.append(f'Producto #{product_id} no existe.')
                    continue
                    
                try:
                    qty = int(item.get('quantity', product.incoming_stock))
                except (ValueError, TypeError):
                    errors.append(f'{product.name}: Cantidad inválida.')
                    continue
                    
                if qty <= 0:
                    continue
                    
                if qty > product.incoming_stock:
                    errors.append(f'{product.name}: Intentaste recibir {qty}, pero solo hay {product.incoming_stock} pendientes.')
                    continue
                    
                purchase_price = item.get('purchase_price')
                if purchase_price is not None:
                    try:
                        purchase_price = Decimal(str(purchase_price))
                    except Exception:
                        purchase_price = product.purchase_price or Decimal('0.00')
                else:
                    purchase_price = product.purchase_price or Decimal('0.00')
                    
                product.incoming_stock -= qty
                product.save(update_fields=['incoming_stock'])
                
                StockEntry.objects.create(
                    product=product,
                    quantity=qty,
                    purchase_price=purchase_price,
                    notes='Recepción masiva de stock en tránsito'
                )
                product.refresh_from_db()
                received_products.append({
                    'id': product.id,
                    'name': product.name,
                    'received_qty': qty,
                    'new_stock': product.stock,
                    'remaining_incoming': product.incoming_stock
                })
                
        if errors and not received_products:
            return Response({'error': ' | '.join(errors)}, status=400)
            
        return Response({
            'message': f'Se recibió stock para {len(received_products)} productos exitosamente.',
            'received_products': received_products,
            'warnings': errors
        })

class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['product']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
    











class RelevantTagsView(views.APIView):
    permission_classes = [permissions.AllowAny] # Los tags relevantes suelen ser públicos
    search_fields = ['name', 'description', 'category__name', 'subcategory__name', 'tags__name', 'brand__name']

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
        
        # Aplicar los filtros de producto (categoría, subcategoría, etc.)
        # utilizando tu ProductFilter existente.
        product_filter = ProductFilter(data=filtering_params, queryset=product_queryset, request=request)
        filtered_products_qs = product_filter.qs # Este es el queryset de productos ya filtrados
        
        # Aplicar el filtro de búsqueda de texto libre
        search_filter = filters.SearchFilter()
        filtered_products_qs = search_filter.filter_queryset(request, filtered_products_qs, self)

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


class RelevantBrandsView(views.APIView):
    permission_classes = [permissions.AllowAny]
    search_fields = ['name', 'description', 'category__name', 'subcategory__name', 'tags__name', 'brand__name']

    def get(self, request, *args, **kwargs):
        product_queryset = Product.objects.all()
        
        filtering_params = request.query_params.copy()
        filtering_params.pop('brand', None)
        filtering_params.pop('brands', None)
        
        product_filter = ProductFilter(data=filtering_params, queryset=product_queryset, request=request)
        filtered_products_qs = product_filter.qs
        
        # Aplicar el filtro de búsqueda de texto libre
        search_filter = filters.SearchFilter()
        filtered_products_qs = search_filter.filter_queryset(request, filtered_products_qs, self)
        
        relevant_brands_qs = Brand.objects.filter(
            products__in=filtered_products_qs 
        ).exclude(
            name__iexact='GENERICO'
        ).annotate(
            product_count=Count('products', filter=Q(products__in=filtered_products_qs))
        ).filter(
            product_count__gt=0
        ).order_by('-product_count', 'name').distinct()

        serializer = RelevantBrandSerializer(relevant_brands_qs, many=True)
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