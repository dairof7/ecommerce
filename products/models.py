from django.utils import timezone
from decimal import Decimal
from django.db import models
# from sales.models import Discount
from decimal import Decimal, ROUND_DOWN
class Category(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField("Imagen de Categoría", upload_to='categories/', blank=True, null=True)
    description = models.TextField("Descripción (opcional)", blank=True)
    display_order = models.PositiveIntegerField(
        "Orden de Visualización", 
        default=0, 
        help_text="Menor número aparece primero. 0 es la prioridad más alta."
    )
    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['display_order', 'name']
    def __str__(self):
        return self.name

class Subcategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    image = models.ImageField("Imagen de Subcategoría", upload_to='subcategories/', blank=True, null=True)
    description = models.TextField("Descripción (opcional)", blank=True)

    class Meta:
        verbose_name = "Subcategoría"
        verbose_name_plural = "Subcategorías"
        ordering = ['category', 'name']
        # Para asegurar que el nombre de la subcategoría sea único dentro de su categoría padre
        unique_together = ('category', 'name') 

    def __str__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    subcategory = models.ForeignKey(Subcategory, on_delete=models.PROTECT)
    description = models.TextField(blank=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    stock = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField("Producto Destacado", default=False, db_index=True)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    # Este 'discount' es el descuento base/individual del producto
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_active_discount_percentage(self):
        from sales.models import Discount
        """
        Encuentra el descuento porcentual más relevante y activo para este producto.
        Prioridad: Producto específico > Subcategoría > Categoría.
        Dentro de cada nivel, podrías tener una lógica para el "mejor" descuento si hay solapamientos.
        Aquí, tomaremos el primero que encuentre en orden de especificidad.
        """
        now = timezone.now()
        active_discounts_qs = Discount.objects.filter(
            start_date__lte=now,
            end_date__gte=now
        ).order_by('product', 'subcategory', 'category') # Ordenar para priorizar

        # 1. Descuento específico del producto
        product_discount = active_discounts_qs.filter(product=self).first()
        if product_discount:
            return product_discount.percentage

        # 2. Descuento de la subcategoría del producto
        if self.subcategory:
            subcategory_discount = active_discounts_qs.filter(subcategory=self.subcategory, product__isnull=True).first()
            if subcategory_discount:
                return subcategory_discount.percentage
        
        # 3. Descuento de la categoría del producto
        if self.category:
            category_discount = active_discounts_qs.filter(category=self.category, subcategory__isnull=True, product__isnull=True).first()
            if category_discount:
                return category_discount.percentage
        
        return Decimal('0.00') # No hay descuentos activos del modelo Discount

    @property
    def final_sale_price(self):
        """
        Calcula el precio de venta final aplicando:
        1. El descuento base del producto (self.discount).
        2. El descuento más relevante del modelo Discount.
        Se podría debatir cuál tiene prioridad o si se acumulan.
        Aquí, aplicaremos primero el self.discount, y luego el del modelo Discount sobre ese resultado,
        o podrías elegir el MAYOR de los dos.
        Por simplicidad, tomemos el descuento del modelo Discount si existe, si no, el self.discount.
        O, una lógica más común: el precio base menos el descuento más ventajoso.
        """
        base_price = self.sale_price
        
        # Aplicar el descuento individual del producto (product.discount)
        price_after_individual_discount = base_price * (Decimal('1.00') - (self.discount / Decimal('100.00')))

        # Obtener el porcentaje del modelo Discount (por categoría/subcategoría/producto)
        dynamic_discount_percentage = self.get_active_discount_percentage()

        # Opción A: Acumular (no siempre deseado)
        # final_price = price_after_individual_discount * (Decimal('1.00') - (dynamic_discount_percentage / Decimal('100.00')))

        # con esta se aplica el descuento más ventajoso - mayor
        # effective_discount_percentage = max(self.discount, dynamic_discount_percentage)
        
        # con esta se aplica el descuento dinamico si el individual no es 0
        effective_discount_percentage = dynamic_discount_percentage if self.discount == 0 else self.discount

        final_price = base_price * (Decimal('1.00') - (effective_discount_percentage / Decimal('100.00')))
        rounded_price = final_price.quantize(Decimal('1E3'), rounding=ROUND_DOWN)
        return rounded_price

    @property
    def active_discount_info(self):
        """Devuelve información sobre el descuento activo, si lo hay."""
        # Similar a get_active_discount_percentage pero devuelve el objeto Discount o info
        now = timezone.now()
        # ... lógica similar para encontrar el descuento más específico ...
        # Podrías devolver el objeto Discount o un diccionario con {type: 'product'/'category', percentage: X}
        return None # Placeholder

    def __str__(self):
        return self.name

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"Image for {self.product.name}"