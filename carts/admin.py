from django.contrib import admin
from .models import Cart, CartItem, Quote

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 1

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    list_filter = ('user',)
    search_fields = ('user__username',)
    inlines = [CartItemInline]

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity')
    list_filter = ('cart', 'product')
    search_fields = ('cart__user__username', 'product__name')

@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ('cart', 'created_at', 'status', 'total')
    list_filter = ('status', 'created_at')
    search_fields = ('cart__user__username',)
    readonly_fields = ('cart', 'total', 'created_at')  # No permitir editar estos campos
    fieldsets = (
        (None, {
            'fields': ('cart', 'created_at', 'total', 'status')
        }),
    )