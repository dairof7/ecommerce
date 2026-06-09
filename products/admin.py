from django.contrib import admin
from .models import Category, Subcategory, Product, ProductImage, Tag
from django.utils.html import format_html

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

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1  # Número de campos de imagen vacíos que se muestran

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id','name', 'category', 'subcategory', 'is_active', 'is_service', 'pp_display', 'average_cost', 'final_price', 'stock', 'discount', 'is_featured')
    list_filter = ('is_active', 'is_service', 'category', 'subcategory', 'tags', 'is_featured')
    search_fields = ('name', 'description')
    list_editable = ('is_active', 'is_service', 'is_featured',)
    inlines = [ProductImageInline]
    filter_horizontal = ('tags',)  # Para una mejor interfaz de selección de tags
    readonly_fields = ('final_price',)
    fieldsets = (
        (None, {
            'fields': ('name', 'description')
        }),
        ('Categorización', {
            'fields': ('category', 'subcategory', 'tags')
        }),
        ('Precios e Inventario', {
            'fields': ('purchase_price', 'average_cost', 'sale_price', 'final_price', 'stock', 'discount')
        }),
        ('Configuración Adicional', {
            'fields': ('is_active', 'is_featured', 'is_service')
        })
    )

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