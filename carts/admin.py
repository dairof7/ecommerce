# carts/admin.py
from django.contrib import admin
from .models import Cart, CartItem, Quote, QuoteItem # Importa QuoteItem

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0 # Mostrar 0 campos vacíos por defecto, solo mostrar los existentes
    readonly_fields = ('subtotal',) # Mostrar el subtotal pero no editarlo


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id','user', 'created_at', 'updated_at')
    list_filter = ('user',)
    search_fields = ('user__username',)
    inlines = [CartItemInline]
    readonly_fields = ('created_at', 'updated_at')

class QuoteItemInline(admin.TabularInline):
    model = QuoteItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price_at_quote', 'subtotal') # Los items de la cotización son de solo lectura
    can_delete = False
    def has_add_permission(self, request, obj=None):
        return False
@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ('id','user', 'created_at', 'status', 'total') # Mostrar user en lugar de cart
    list_filter = ('status', 'created_at', 'user')
    search_fields = ('user__username',) # Buscar por nombre de usuario
    readonly_fields = ('user', 'cart', 'created_at', 'updated_at', 'total') # Campos de solo lectura
    inlines = [QuoteItemInline] # Mostrar los items de la cotización

    fieldsets = (
        (None, {
            'fields': ('user', 'cart', 'created_at', 'updated_at', 'status', 'total')
        }),
        # Los items se mostrarán a través del inline
    )

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('id','cart', 'product', 'quantity', 'subtotal') # Mostrar subtotal
    list_filter = ('cart__user', 'product') # Filtrar por usuario del carrito y producto
    search_fields = ('cart__user__username', 'product__name')
    readonly_fields = ('subtotal',)

# Registrar QuoteItem (aunque se verá principalmente como inline en Quote)
@admin.register(QuoteItem)
class QuoteItemAdmin(admin.ModelAdmin):
    list_display = ('id','quote', 'product', 'quantity', 'price_at_quote', 'subtotal')
    list_filter = ('quote__user', 'product', 'quote__status') # Filtrar por usuario de la cotización, producto y estado de la cotización
    search_fields = ('quote__user__username', 'product__name', 'quote__id')
    readonly_fields = ('quote', 'product', 'quantity', 'price_at_quote', 'subtotal')