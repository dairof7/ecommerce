# carts/serializers.py
from rest_framework import serializers
from .models import Cart, CartItem, Quote, QuoteItem
from products.models import Product # Asegúrate de importar Product

class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    product_sale_price = serializers.ReadOnlyField(source='product.sale_price')
    # Incluir el subtotal del item del carrito
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)


    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_name', 'quantity', 'product_sale_price', 'subtotal']
        # Al añadir/actualizar un item, solo permitimos enviar product y quantity
        read_only_fields = ('cart', 'product_name', 'product_sale_price', 'subtotal') # No permitir modificar estos campos directamente
        extra_kwargs = {
            'product': {'write_only': True} # El ID del producto se envía al crear/actualizar
        }


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    # Puedes añadir un campo para el total del carrito si lo deseas
    # cart_total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'created_at', 'updated_at']
        read_only_fields = ('user', 'created_at', 'updated_at') # El usuario y fechas no se modifican directamente

    # def get_cart_total(self, obj):
    #    return sum(item.subtotal for item in obj.items.all())


class QuoteItemSerializer(serializers.ModelSerializer):
    # Mostrar detalles relevantes del producto en el item de la cotización
    product_name = serializers.ReadOnlyField(source='product.name')
    product_description = serializers.ReadOnlyField(source='product.description')
    # Puedes incluir otras cosas como imágenes si las necesitas aquí

    class Meta:
        model = QuoteItem
        fields = ['id', 'product', 'product_name', 'product_description', 'quantity', 'price_at_quote', 'subtotal']
        # read_only_fields = '__all__' # Los items de la cotización no se modifican una vez creados
        read_only_fields = ('id', 'product', 'product_name', 'product_description', 'quantity', 'price_at_quote', 'subtotal')
class QuoteSerializer(serializers.ModelSerializer):
    # Incluir los items de la cotización anidados
    items = QuoteItemSerializer(many=True, read_only=True)
    user = serializers.ReadOnlyField(source='user.username') # Mostrar el nombre de usuario

    class Meta:
        model = Quote
        fields = ['id', 'user', 'cart', 'created_at', 'updated_at', 'status', 'total', 'items']
        read_only_fields = ('user', 'cart', 'created_at', 'updated_at', 'total', 'items') # No permitir modificar estos campos