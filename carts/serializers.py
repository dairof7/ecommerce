# carts/serializers.py
from rest_framework import serializers
from .models import Cart, CartItem, Quote, QuoteItem
from products.models import Product # Asegúrate de importar Product
from accounts.serializers import UserProfileSerializer
class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    product_id = serializers.ReadOnlyField(source='product.id')
    product_sale_price = serializers.ReadOnlyField(source='product.sale_price')
    product_final_price = serializers.ReadOnlyField(source='product.final_sale_price')
    # Incluir el subtotal del item del carrito
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    product_image_url = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_name', 'quantity', 'product_sale_price','product_final_price', 'subtotal', 'product_image_url', 'product_id']
        # Al añadir/actualizar un item, solo permitimos enviar product y quantity
        read_only_fields = ('cart', 'product_name', 'product_sale_price', 'product_final_price','subtotal', 'product_image') # No permitir modificar estos campos directamente
        extra_kwargs = {
            'product': {'write_only': True} # El ID del producto se envía al crear/actualizar
        }
    def get_product_image_url(self, obj: CartItem):
        # obj es la instancia de CartItem
        # obj.product es la instancia de Product relacionada
        first_image = obj.product.images.first() # Obtiene el primer ProductImage asociado al producto
        if first_image and first_image.image:
            request = self.context.get('request') # Necesitas el contexto del request para build_absolute_uri
            if request:
                return request.build_absolute_uri(first_image.image.url)
            return first_image.image.url # Fallback si no hay request en el contexto
        return None # O una URL de placeholder: 'https://via.placeholder.com/150'

class CartSerializer(serializers.ModelSerializer):
    # items = CartItemSerializer(many=True, read_only=True)
    items = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'created_at', 'updated_at']
        read_only_fields = ('user', 'itemCount', 'totalAmount', 'created_at', 'updated_at')

    def get_items(self, obj):
        ordered_items = obj.items.all().order_by('product__name') # O 'added_at'
        return CartItemSerializer(ordered_items, many=True, context=self.context).data


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
    user_email = serializers.ReadOnlyField(source='user.email')
    user_detail = UserProfileSerializer(source='user.profile', read_only=True) 

    # class Meta:
    #     model = Quote
    #     fields = ['id', 'user', 'cart', 'created_at', 'updated_at', 'status', 'total', 'items', 'user_detail']
    #     read_only_fields = ('user', 'cart', 'created_at', 'updated_at', 'total', 'items') # No permitir modificar estos campos
    class Meta:
        model = Quote
        fields = [
            'id', 
            'user', # Sigue siendo útil para la asociación
            'user_email', # Para mostrar
            # Nuevos campos de cliente invitado
            'customer_name',
            'customer_email',
            'customer_document',
            'customer_phone',
            # Campos existentes
            'cart', 
            'created_at', 
            'updated_at', 
            'status', 
            'total', 
            'items',
            'user_detail'
        ]
        # Hacemos 'user' de solo lectura porque se establecerá automáticamente
        # si la solicitud la hace un usuario autenticado, no se debe poder asignar manualmente.
        read_only_fields = ['user', 'cart', 'created_at', 'updated_at', 'total', 'items', 'user_email']