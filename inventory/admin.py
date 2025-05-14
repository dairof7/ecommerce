from django.contrib import admin
from .models import StockEntry

@admin.register(StockEntry)
class StockEntryAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'purchase_price', 'date')
    list_filter = ('product', 'date')
    search_fields = ('product__name',)
    date_hierarchy = 'date' # Navegación jerárquica por fechas
    readonly_fields = ('date',)

    fieldsets = (
        (None, {
            'fields': ('product', 'quantity', 'purchase_price')
        }),
        ('Información Adicional', {
            'fields': ('notes',)
        }),
    )