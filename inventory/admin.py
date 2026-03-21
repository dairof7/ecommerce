from django.contrib import admin
from django.urls import path
from django.http import JsonResponse
from .models import StockEntry
from products.models import Product

@admin.register(StockEntry)
class StockEntryAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'purchase_price', 'date')
    list_filter = ('product', 'date')
    search_fields = ('product__name',)
    date_hierarchy = 'date' # Navegación jerárquica por fechas
    autocomplete_fields = ['product'] # Habilita un widget con buscador para el campo 'product'.
    readonly_fields = ('date',)

    fieldsets = (
        (None, {
            'fields': ('product', 'quantity', 'purchase_price')
        }),
        ('Información Adicional', {
            'fields': ('notes',)
        }),
    )

    class Media:
        js = ('inventory/js/admin_stockentry.js',)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('get_product_price/<int:product_id>/', 
                 self.admin_site.admin_view(self.get_product_price), 
                 name='inventory_stockentry_get_product_price'),
        ]
        return custom_urls + urls

    def get_product_price(self, request, product_id):
        try:
            product = Product.objects.get(pk=product_id)
            price = str(product.purchase_price) if product.purchase_price is not None else ""
            return JsonResponse({'purchase_price': price})
        except Product.DoesNotExist:
            return JsonResponse({'error': 'Product not found'}, status=404)