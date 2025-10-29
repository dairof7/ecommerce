from decimal import Decimal
from rest_framework import serializers
from .models import Category, Subcategory, Product, ProductImage, Tag





class CategorySerializer(serializers.ModelSerializer):
    image = serializers.ImageField(read_only=True)
    # Si se requiere permitir la subida de imágenes a través de la API:
    # image_upload = serializers.ImageField(source='image', write_only=True, required=False)
    class Meta:
        model = Category
        fields = ['id', 'name', 'image', 'description', 'is_active'] # Añadir image y description
        # Si se usa image_upload:
        # fields = ['id', 'name', 'image', 'description', 'image_upload']
        # fields = '__all__'

class SubcategorySerializer(serializers.ModelSerializer):
    image = serializers.ImageField(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(read_only=True, source='category.id')
    class Meta:
        model = Subcategory
        fields = ['id', 'name', 'image', 'description', 'category_id', 'is_active']
        # fields = '__all__'

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']

# Nuevo Serializador para Tags con conteo de productos
class RelevantTagSerializer(TagSerializer): # Hereda de TagSerializer
    product_count = serializers.IntegerField(read_only=True)

    class Meta(TagSerializer.Meta): # Hereda Meta de TagSerializer
        fields = TagSerializer.Meta.fields + ['product_count']

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text']

class ProductSerializer(serializers.ModelSerializer):
    # Campos para mostrar (read-only) con serializadores anidados
    category = CategorySerializer(read_only=True) # Para mostrar el objeto categoría completo
    subcategory = SubcategorySerializer(read_only=True) # Para mostrar el objeto subcategoría completo
    images = ProductImageSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True) # Para mostrar los objetos tag completos

    final_sale_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    # Opcional: mostrar el precio original y el porcentaje de descuento aplicado
    original_sale_price = serializers.DecimalField(source='sale_price', max_digits=10, decimal_places=2, read_only=True)
    applied_discount_percentage = serializers.SerializerMethodField(read_only=True)
    
    # Campos adicionales para mostrar claramente el descuento
    discount_amount_saved = serializers.SerializerMethodField()
    has_discount = serializers.SerializerMethodField()



    # Campos para la entrada (write-only o para creación/actualización)
    # Estos aceptarán IDs al crear/actualizar
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )
    subcategory_id = serializers.PrimaryKeyRelatedField(
        queryset=Subcategory.objects.all(), source='subcategory', write_only=True
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), source='tags', many=True, write_only=True, required=False
    )
    # 'source' le dice a DRF a qué campo del modelo mapear este campo del serializador.
    # 'write_only=True' significa que estos campos solo se usan para entrada, no se mostrarán en la salida.
    # 'required=False' para tag_ids si los tags son opcionales.

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description',
            'original_sale_price',      # Precio antes de cualquier descuento
            'discount',               # El campo 'discount' base del producto, podrías incluirlo si es relevante para el front
            'applied_discount_percentage', # El % total de descuento que se está aplicando
            'discount_amount_saved',    # El monto ahorrado
            'final_sale_price',         # Precio final a pagar
            'has_discount',             # Booleano para UI
            'stock',
            'is_active',
            'is_service',
            'is_featured',
            'created_at', 'updated_at',
            'category', 'subcategory', 'images', 'tags',
            'category_id', 'subcategory_id', 'tag_ids'
        ]
        read_only_fields = ('stock', 'created_at', 'updated_at')

    def get_applied_discount_percentage(self, obj) -> Decimal:
        # Esta lógica debe ser consistente con cómo se calcula final_sale_price en el modelo
        # Asumimos que final_sale_price ya considera el mejor descuento.
        # Si original_sale_price es 0, evitamos división por cero.
        if obj.sale_price and obj.sale_price > Decimal('0.00'):
            # Porcentaje = ((PrecioOriginal - PrecioFinal) / PrecioOriginal) * 100
            # Asegurarse que obj.final_sale_price está disponible (es una @property)
            percentage = ((obj.sale_price - obj.final_sale_price) / obj.sale_price) * Decimal('100.00')
            return percentage.quantize(Decimal("0.01")) # Redondear
        return Decimal('0.00')

    def get_discount_amount_saved(self, obj: Product) -> Decimal:
        # MontoAhorrado = PrecioOriginal - PrecioFinal
        amount = obj.sale_price - obj.final_sale_price
        return amount.quantize(Decimal("0.01"))

    def get_has_discount(self, obj: Product) -> bool:
        return obj.final_sale_price < obj.sale_price

    def validate(self, data):
        # Validar que la subcategoría pertenezca a la categoría
        # Esto es importante si category_id y subcategory_id se envían
        category = data.get('category') # Obtenido de category_id a través de source='category'
        subcategory = data.get('subcategory') # Obtenido de subcategory_id a través de source='subcategory'

        if category and subcategory:
            if subcategory.category != category:
                raise serializers.ValidationError({
                    "subcategory_id": "La subcategoría seleccionada no pertenece a la categoría especificada."
                })
        return data
    
    # DRF maneja la asignación de ManyToManyField (como tags a través de tag_ids)
    # automáticamente en create y update si usas PrimaryKeyRelatedField con source y many=True.
    # No necesitas sobrescribir create() o update() solo para esto.