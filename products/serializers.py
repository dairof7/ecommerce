from decimal import Decimal
from rest_framework import serializers
from .models import Category, Subcategory, Product, ProductImage, Tag, Brand, Supplier





class CategorySerializer(serializers.ModelSerializer):
    image = serializers.ImageField(read_only=True)
    name = serializers.SerializerMethodField()
    
    # Si se requiere permitir la subida de imágenes a través de la API:
    # image_upload = serializers.ImageField(source='image', write_only=True, required=False)
    class Meta:
        model = Category
        fields = ['id', 'name', 'image', 'description', 'is_active'] # Añadir image y description
        
    def get_name(self, obj):
        return obj.name.title() if obj.name else ""
        # Si se usa image_upload:
        # fields = ['id', 'name', 'image', 'description', 'image_upload']
        # fields = '__all__'

class SubcategorySerializer(serializers.ModelSerializer):
    image = serializers.ImageField(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(read_only=True, source='category.id')
    name = serializers.SerializerMethodField()
    
    class Meta:
        model = Subcategory
        fields = ['id', 'name', 'image', 'description', 'category_id', 'is_active']
        
    def get_name(self, obj):
        return obj.name.title() if obj.name else ""
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

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name']

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ['id', 'name']

class RelevantBrandSerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Brand
        fields = ['id', 'name', 'product_count']

class ProductImageSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True, required=False
    )

    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'product', 'product_id']
        read_only_fields = ['product']

class ProductSerializer(serializers.ModelSerializer):
    # Campos para mostrar (read-only) con serializadores anidados
    category = CategorySerializer(read_only=True) # Para mostrar el objeto categoría completo
    subcategory = SubcategorySerializer(read_only=True) # Para mostrar el objeto subcategoría completo
    brand = BrandSerializer(read_only=True)
    supplier = SupplierSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True) # Para mostrar los objetos tag completos

    sale_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    purchase_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    average_cost = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    final_sale_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    original_sale_price = serializers.DecimalField(source='sale_price', max_digits=10, decimal_places=2, read_only=True)
    applied_discount_percentage = serializers.SerializerMethodField(read_only=True)
    
    # Campos adicionales para mostrar claramente el descuento
    discount_amount_saved = serializers.SerializerMethodField()
    has_discount = serializers.SerializerMethodField()

    brand_name = serializers.CharField(source='brand.name', read_only=True, default='', allow_null=True)

    # Campos para la entrada (write-only o para creación/actualización)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )
    subcategory_id = serializers.PrimaryKeyRelatedField(
        queryset=Subcategory.objects.all(), source='subcategory', write_only=True
    )
    brand_id = serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all(), source='brand', write_only=True, required=False, allow_null=True
    )
    supplier_id = serializers.PrimaryKeyRelatedField(
        queryset=Supplier.objects.all(), source='supplier', write_only=True, required=False, allow_null=True
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), source='tags', many=True, write_only=True, required=False
    )

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description',
            'sale_price',
            'original_sale_price',
            'purchase_price',
            'average_cost',
            'discount',
            'applied_discount_percentage',
            'discount_amount_saved',
            'final_sale_price',
            'has_discount',
            'stock',
            'incoming_stock',
            'is_active',
            'is_service',
            'is_combo',
            'is_featured',
            'created_at', 'updated_at',
            'category', 'subcategory', 'brand', 'supplier', 'images', 'tags',
            'brand_name',
            'category_id', 'subcategory_id', 'brand_id', 'supplier_id', 'tag_ids'
        ]
        read_only_fields = ('created_at', 'updated_at', 'brand_name')

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