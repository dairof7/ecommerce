from django.contrib import admin
from .models import Discount

@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ('category', 'subcategory', 'product', 'percentage', 'start_date', 'end_date')
    list_filter = ('category', 'subcategory')
    search_fields = ('category__name', 'subcategory__name', 'product__name')
    date_hierarchy = 'start_date' # Para navegar por fechas
    # opcion buscar usando popup
    # raw_id_fields = ('product', 'category', 'subcategory')
    # opcion B autocomplete requiere que los modelos tengan los campos en search_fields
    autocomplete_fields = ['product', 'category', 'subcategory']
    fieldsets = (
        (None, {
            'fields': ('percentage', 'start_date', 'end_date')
        }),
        ('Aplicar a', {
            'fields': ('category', 'subcategory', 'product')
        }),
    )