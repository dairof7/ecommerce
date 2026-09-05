from django.contrib import admin
from .models import Category, Subcategory, Product, ProductImage, Tag, Brand, Supplier, ProductPricing
from django.db import models
from django.forms import NumberInput
from django.template.response import TemplateResponse
from django.http import HttpResponseRedirect
from django.utils.html import format_html
from django.contrib import messages
from django.contrib.admin import RelatedFieldListFilter

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
    list_display = ('image_thumbnail', 'name', 'brand', 'pp_display','sale_price','final_price', 'stock', 'discount', 'is_active', 'is_service', 'is_combo', 'is_featured', 'category', 'subcategory')
    list_display_links = ('image_thumbnail', 'name')
    list_filter = ('is_active', 'is_service', 'is_combo', ('category', DropdownFilter), ('subcategory', DropdownFilter), ('brand', DropdownFilter), ('supplier', DropdownFilter), ('tags', DropdownFilter), 'is_featured')
    search_fields = ('name', 'description', 'brand__name')
    list_editable = ('is_active', 'is_service', 'is_combo', 'is_featured',)
    list_per_page = 25
    list_select_related = ('brand', 'category', 'subcategory')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('images')
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
        ('Configuración Adicional', {
            'fields': ('is_active', 'is_featured', 'is_service', 'is_combo')
        })
    )
    
    def pp_display(self, obj):
        return obj.purchase_price
    pp_display.short_description = 'PP'

    def final_price(self, obj):
        return obj.final_sale_price
    final_price.short_description = 'PF (-disc)'

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
    list_display = ('image_thumbnail', 'product_name_link', 'purchase_price',  'sale_price', 'discount', 'final_price', 'net_profit', 'profit_margin', 'stock', 'incoming_stock', 'is_active')
    list_display_links = ('image_thumbnail',)
    list_editable = ('purchase_price', 'sale_price', 'discount', 'incoming_stock', 'is_active')
    list_filter = ('is_active', StockStatusFilter, ('brand', DropdownFilter), ('supplier', DropdownFilter), ('category', DropdownFilter), ('subcategory', DropdownFilter), ('tags', DropdownFilter))
    search_fields = ('name',)
    list_per_page = 25
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('images')
    
    formfield_overrides = {
        models.DecimalField: {'widget': NumberInput(attrs={'style': 'width: 80px;'})},
        models.IntegerField: {'widget': NumberInput(attrs={'style': 'width: 70px;'})},
    }
    
    fieldsets = (
        (None, {
            'fields': ('name',)
        }),
        ('Precios e Inventario', {
            'fields': ('purchase_price', 'sale_price', 'discount', 'final_price', 'net_profit', 'profit_margin', 'stock', 'incoming_stock')
        }),
    )
    readonly_fields = ('name', 'stock', 'final_price', 'net_profit', 'profit_margin')

    def product_name_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:products_product_change', args=[obj.pk])
        return format_html('<a href="{}" title="Ir a Detalles del Producto">{}</a>', url, obj.name)
    product_name_link.short_description = 'Name'
    product_name_link.admin_order_field = 'name'

    def final_price(self, obj):
        return obj.final_sale_price
    final_price.short_description = 'PF (-disc)'

    def net_profit(self, obj):
        if obj.purchase_price is not None:
            return obj.final_sale_price - obj.purchase_price
        return "-"
    net_profit.short_description = 'Ganancia ($)'

    def profit_margin(self, obj):
        if obj.purchase_price and obj.purchase_price > 0:
            margin = ((obj.final_sale_price - obj.purchase_price) / obj.purchase_price) * 100
            return f"{margin:.2f}%"
        return "-"
    profit_margin.short_description = 'Ganancia (%)'

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
        
        if not products_to_receive.exists():
            self.message_user(request, "No se seleccionó ningún producto con stock en tránsito pendiente.", level=messages.WARNING)
            return
            
        if 'apply' in request.POST:
            count = 0
            for product in products_to_receive:
                try:
                    received_qty = int(request.POST.get(f'received_{product.id}', 0))
                except (ValueError, TypeError):
                    received_qty = 0
                    
                if received_qty > 0:
                    if received_qty > product.incoming_stock:
                        self.message_user(request, f"Error: {product.name} (Intentaste recibir {received_qty}, pero solo hay {product.incoming_stock} pendientes).", level=messages.ERROR)
                        continue
                        
                    product.incoming_stock -= received_qty
                    product.save(update_fields=['incoming_stock'])
                    
                    StockEntry.objects.create(
                        product=product,
                        quantity=received_qty,
                        purchase_price=product.purchase_price or Decimal('0.00'),
                        notes=f"Recepción de stock en tránsito desde Panel Rápido"
                    )
                    count += 1

            if count > 0:
                self.message_user(request, f"Se recibió stock para {count} productos.", level=messages.SUCCESS)
            return HttpResponseRedirect(request.get_full_path())
            
        context = dict(
            self.admin_site.each_context(request),
            title="Confirmar Recepción de Stock en Tránsito",
            queryset=products_to_receive,
            action_checkbox_name=admin.helpers.ACTION_CHECKBOX_NAME,
        )
        
        return TemplateResponse(request, 'admin/receive_stock_intermediate.html', context)
        
    receive_incoming_stock.short_description = "Recibir Stock en Tránsito (Permite recepción parcial)"