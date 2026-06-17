from django.contrib import admin
from .models import Category, Subcategory, Product, ProductImage, Tag, Brand, Supplier, ProductPricing
from django.utils.html import format_html
from django.contrib import messages
from django.contrib.admin import RelatedFieldListFilter
from .tasks import update_cop_costs_from_usd
from decimal import Decimal
from inventory.models import StockEntry

class DropdownFilter(RelatedFieldListFilter):
    template = 'admin/dropdown_filter.html'

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_active', 'display_order','image_thumbnail', 'description_short') # Añadir miniatura
    search_fields = ('name', 'description')
    list_editable = ('is_active', 'display_order',)
    # Para mostrar la imagen en el formulario de edición y permitir la subida:
    fields = ('name', 'description', 'image', 'image_preview') # 'image' es el campo de subida
    readonly_fields = ('image_preview',) # Para mostrar la vista previa
    ordering = ('display_order', 'name')
    
    def image_thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 45px; height:45px; object-fit:cover;" />', obj.image.url)
        return "-"
    image_thumbnail.short_description = 'Miniatura'

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-width: 200px; max-height:200px;" />', obj.image.url)
        return "(Ninguna imagen)"
    image_preview.short_description = 'Vista Previa de Imagen'
    
    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Descripción'

@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'is_active', 'image_thumbnail', 'description_short')
    list_filter = ('category', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('name', 'description', 'category__name')
    fields = ('name', 'category', 'description', 'image', 'image_preview')
    readonly_fields = ('image_preview',)

    def image_thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 45px; height:45px; object-fit:cover;" />', obj.image.url)
        return "-"
    image_thumbnail.short_description = 'Miniatura'

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-width: 200px; max-height:200px;" />', obj.image.url)
        return "(Ninguna imagen)"
    image_preview.short_description = 'Vista Previa de Imagen'

    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Descripción'

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1  # Número de campos de imagen vacíos que se muestran

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id','name', 'category', 'subcategory', 'brand', 'is_active', 'is_service', 'is_combo', 'pp_display', 'reference_usd_cost', 'reference_cop_cost', 'final_price', 'stock', 'discount', 'is_featured')
    list_filter = ('is_active', 'is_service', 'is_combo', ('category', DropdownFilter), ('subcategory', DropdownFilter), ('brand', DropdownFilter), ('supplier', DropdownFilter), ('tags', DropdownFilter), 'is_featured')
    search_fields = ('name', 'description')
    list_editable = ('is_active', 'is_service', 'is_combo', 'is_featured',)
    inlines = [ProductImageInline]
    filter_horizontal = ('tags',)  # Para una mejor interfaz de selección de tags
    readonly_fields = ('final_price',)
    fieldsets = (
        (None, {
            'fields': ('name', 'description')
        }),
        ('Categorización', {
            'fields': ('category', 'subcategory', 'brand', 'supplier', 'tags')
        }),
        ('Precios e Inventario', {
            'fields': ('purchase_price', 'average_cost', 'sale_price', 'final_price', 'stock', 'discount')
        }),
        ('Costos de Importación (Solo Admin)', {
            'fields': ('reference_usd_cost', 'reference_cop_cost'),
            'classes': ('collapse',)
        }),
        ('Configuración Adicional', {
            'fields': ('is_active', 'is_featured', 'is_service', 'is_combo')
        })
    )
    
    actions = ['force_update_cop_costs']

    def force_update_cop_costs(self, request, queryset):
        # Esta acción no requiere procesar el queryset porque la tarea busca todos los productos con USD cost
        # Pero podemos procesar el queryset si quisieramos. En este caso actualizamos todos.
        result_message = update_cop_costs_from_usd()
        if "Éxito" in result_message:
            self.message_user(request, result_message, level=messages.SUCCESS)
        else:
            self.message_user(request, result_message, level=messages.ERROR)
            
    force_update_cop_costs.short_description = "Sincronizar Costos COP desde USD (Tasa de Cambio Actual)"

    def pp_display(self, obj):
        return obj.purchase_price
    pp_display.short_description = 'PP'

    def final_price(self, obj):
        return obj.final_sale_price
    final_price.short_description = 'PF (-disc)'

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'image', 'alt_text')
    search_fields = ('product__name', 'alt_text')
    list_filter = ('product',)

class StockStatusFilter(admin.SimpleListFilter):
    title = 'Estado de Inventario'
    parameter_name = 'stock_status'

    def lookups(self, request, model_admin):
        return (
            ('in_stock', 'Con Stock (>0)'),
            ('out_of_stock', 'Sin Stock (0)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'in_stock':
            return queryset.filter(stock__gt=0)
        if self.value() == 'out_of_stock':
            return queryset.filter(stock=0)
        return queryset

@admin.register(ProductPricing)
class ProductPricingAdmin(admin.ModelAdmin):
    list_display = ('id', 'image_thumbnail', 'name', 'purchase_price', 'reference_usd_cost', 'reference_cop_cost', 'sale_price', 'stock', 'incoming_stock', 'is_active')
    list_display_links = ('id', 'name')
    list_editable = ('purchase_price', 'reference_usd_cost', 'reference_cop_cost', 'sale_price', 'incoming_stock', 'is_active')
    list_filter = ('is_active', StockStatusFilter, ('brand', DropdownFilter), ('supplier', DropdownFilter), ('category', DropdownFilter), ('subcategory', DropdownFilter), ('tags', DropdownFilter))
    search_fields = ('name',)
    list_per_page = 100
    
    fieldsets = (
        (None, {
            'fields': ('name',)
        }),
        ('Precios e Inventario', {
            'fields': ('purchase_price', 'reference_usd_cost', 'reference_cop_cost', 'sale_price', 'stock', 'incoming_stock')
        }),
    )
    readonly_fields = ('name', 'stock')

    def image_thumbnail(self, obj):
        image = obj.images.first()
        if image and image.image:
            return format_html(
                '<img src="{}" style="width: 45px; height:45px; object-fit:cover; border-radius: 4px; transition: transform .2s;" '
                'onmouseover="this.style.transform=\'scale(3)\'; this.style.zIndex=\'100\'; this.style.position=\'relative\';" '
                'onmouseout="this.style.transform=\'scale(1)\'; this.style.zIndex=\'1\'; this.style.position=\'static\';" />',
                image.image.url
            )
        return "-"
    image_thumbnail.short_description = 'Img'

    def has_add_permission(self, request):
        return False # No queremos que agreguen productos desde aquí
        
    actions = ['receive_incoming_stock']
    
    def receive_incoming_stock(self, request, queryset):
        products_to_receive = queryset.filter(incoming_stock__gt=0)
        count = 0
        
        for product in products_to_receive:
            quantity_to_receive = product.incoming_stock
            
            # 1. Poner a cero el stock en tránsito y guardar
            product.incoming_stock = 0
            product.save(update_fields=['incoming_stock'])
            
            # 2. Crear el StockEntry. Esto dispara el signal que suma el stock real
            # y actualiza el costo promedio.
            StockEntry.objects.create(
                product=product,
                quantity=quantity_to_receive,
                purchase_price=product.purchase_price or Decimal('0.00'),
                notes="Recepción automática de stock en tránsito desde Panel Rápido"
            )
            count += 1
            
        if count > 0:
            self.message_user(request, f"Se recibió stock en tránsito para {count} productos. Los registros de inventario fueron creados automáticamente.", level=messages.SUCCESS)
        else:
            self.message_user(request, "No se seleccionó ningún producto con stock en tránsito pendiente.", level=messages.WARNING)
            
    receive_incoming_stock.short_description = "Recibir Stock en Tránsito (Crea registro y suma a Bodega)"