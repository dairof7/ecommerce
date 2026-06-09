from django.contrib import admin
from django import forms
from django.urls import path
from django.http import JsonResponse
from .models import StockEntry
from products.models import Product

class StockEntryAdminForm(forms.ModelForm):
    update_sale_price = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False,
        label="Precio de Venta",
        help_text="Opcional. Puedes actualizar el precio de venta actual del producto desde aquí."
    )

    class Meta:
        model = StockEntry
        fields = '__all__'

@admin.register(StockEntry)
class StockEntryAdmin(admin.ModelAdmin):
    form = StockEntryAdminForm
    list_display = ('product', 'quantity', 'purchase_price', 'date')
    list_filter = ('product', 'date')
    search_fields = ('product__name',)
    date_hierarchy = 'date' # Navegación jerárquica por fechas
    autocomplete_fields = ['product'] # Habilita un widget con buscador para el campo 'product'.
    readonly_fields = ('date',)

    fieldsets = (
        (None, {
            'fields': ('product', 'quantity', 'purchase_price', 'update_sale_price')
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

    def save_model(self, request, obj, form, change):
        # Actualizamos el precio de venta si se proporcionó un valor
        update_sale_price = form.cleaned_data.get('update_sale_price')
        if update_sale_price is not None:
            obj.product.sale_price = update_sale_price
            obj.product.save(update_fields=['sale_price'])
        super().save_model(request, obj, form, change)

    def get_product_price(self, request, product_id):
        try:
            product = Product.objects.get(pk=product_id)
            purchase_price = str(product.purchase_price) if product.purchase_price is not None else ""
            sale_price = str(product.sale_price) if product.sale_price is not None else ""
            return JsonResponse({'purchase_price': purchase_price, 'sale_price': sale_price})
        except Product.DoesNotExist:
            return JsonResponse({'error': 'Product not found'}, status=404)