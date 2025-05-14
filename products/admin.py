from django.contrib import admin
from .models import Category, Subcategory, Product, ProductImage, Tag

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)
    search_fields = ('name',)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1  # Número de campos de imagen vacíos que se muestran

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'subcategory', 'sale_price', 'stock')
    list_filter = ('category', 'subcategory', 'tags')
    search_fields = ('name', 'description')
    inlines = [ProductImageInline]
    filter_horizontal = ('tags',)  # Para una mejor interfaz de selección de tags
    fieldsets = (
        (None, {
            'fields': ('name', 'description')
        }),
        ('Categorización', {
            'fields': ('category', 'subcategory', 'tags')
        }),
        ('Precios e Inventario', {
            'fields': ('purchase_price', 'sale_price', 'stock', 'discount')
        }),
    )

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'image', 'alt_text')
    search_fields = ('product__name', 'alt_text')
    list_filter = ('product',)