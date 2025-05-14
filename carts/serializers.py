from rest_framework import serializers
from .models import Cart, CartItem, Quote

class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    product_sale_price = serializers.ReadOnlyField(source='product.sale_price')

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_name', 'quantity', 'product_sale_price']

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'created_at']

class QuoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quote
        fields = '__all__'
        read_only_fields = ['cart', 'total']