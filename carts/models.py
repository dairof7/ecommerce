from django.db import models
from django.contrib.auth import get_user_model
from products.models import Product
from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError

User = get_user_model()

class Coupon(models.Model):
    code = models.CharField("Código", max_length=50, unique=True)
    valid_from = models.DateTimeField("Válido desde")
    valid_to = models.DateTimeField("Válido hasta")
    discount_type = models.CharField(
        "Tipo",
        max_length=15,
        choices=[('percentage', 'Porcentaje'), ('fixed', 'Monto Fijo')],
    )
    discount_value = models.DecimalField("Valor", max_digits=10, decimal_places=2, help_text="Si es porcentaje, 10.00 para 10%. Si es fijo, el monto.")
    max_discount_amount = models.DecimalField("Máx Desc", max_digits=10, decimal_places=2, null=True, blank=True, help_text="Para descuentos de porcentaje, el monto máximo a descontar.")
    min_purchase_amount = models.DecimalField("Compra Mín", max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    uses_limit = models.PositiveIntegerField("Total Usos", default=1, help_text="Número total de veces que se puede usar el cupón.")
    uses_count = models.PositiveIntegerField("Usado", default=0, editable=False)

    is_active = models.BooleanField("Activo", default=True)

    class Meta:
        verbose_name = "Cupón"
        verbose_name_plural = "Cupones"
        ordering = ['-valid_to']

    def __str__(self):
        return self.code

    def clean(self):
        if self.discount_type == 'percentage' and (self.discount_value <= 0 or self.discount_value > 100):
            raise ValidationError({'discount_value': 'El porcentaje debe ser mayor que 0 y menor o igual a 100.'})
        if self.discount_type == 'fixed' and self.discount_value <= 0:
            raise ValidationError({'discount_value': 'El monto fijo debe ser mayor que 0.'})
        if self.max_discount_amount is not None and self.discount_type != 'percentage':
            raise ValidationError({'max_discount_amount': 'El monto máximo de descuento solo aplica a cupones de porcentaje.'})

    def is_valid(self):
        """Verifica si el cupón está activo, dentro de la fecha y no ha excedido los usos."""
        now = timezone.now()
        return self.is_active and self.valid_from <= now <= self.valid_to and self.uses_count < self.uses_limit

    def calculate_discount(self, amount: Decimal) -> Decimal:
        """Calcula el monto del descuento basado en las reglas del cupón."""
        if self.discount_type == 'percentage':
            discount = amount * (self.discount_value / 100)
            if self.max_discount_amount and discount > self.max_discount_amount:
                return self.max_discount_amount.quantize(Decimal('0.01'))
            return discount.quantize(Decimal('0.01'))
        elif self.discount_type == 'fixed':
            # El descuento fijo no puede ser mayor que el monto de la compra
            return min(self.discount_value, amount).quantize(Decimal('0.01'))
        return Decimal('0.00')

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True, related_name='carts', verbose_name="Cupón")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.user.username}"

    @property
    def subtotal(self) -> Decimal:
        """Calcula el subtotal de todos los items en el carrito."""
        return sum(item.subtotal for item in self.items.all())

    @property
    def coupon_discount(self) -> Decimal:
        """Calcula el descuento del cupón si es aplicable."""
        if not self.coupon:
            return Decimal('0.00')

        # Re-validar el cupón
        if not self.coupon.is_valid() or self.subtotal < self.coupon.min_purchase_amount:
            return Decimal('0.00')

        return self.coupon.calculate_discount(self.subtotal)

    @property
    def total(self) -> Decimal:
        """Calcula el total final del carrito (subtotal - descuento)."""
        return self.subtotal - self.coupon_discount

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def subtotal(self):
        # price_after_discount = self.product.sale_price * (1 - self.product.discount / 100)
        return self.product.final_sale_price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Cart {self.cart.id}"

class Quote(models.Model):
    user = models.ForeignKey(User,
    on_delete=models.SET_NULL, # Si se borra el usuario, la cotización no se borra, solo se desvincula.
    null=True, 
    blank=True, 
    related_name='quotes',
    verbose_name="Usuario"
    )
    customer_name = models.CharField("Nombre", max_length=150, blank=True)
    customer_email = models.EmailField("Email", blank=True)
    customer_document = models.CharField("Documento", max_length=30, blank=True)
    customer_phone = models.CharField("Teléfono", max_length=30, blank=True)
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True, related_name='quotes_used', verbose_name="Cupón Aplicado")
    coupon_discount = models.DecimalField("Descuento por Cupón", max_digits=12, decimal_places=2, default=Decimal('0.00'))
    cart = models.ForeignKey(Cart, on_delete=models.SET_NULL, null=True, blank=True) # Usar SET_NULL si el carrito se elimina

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('paid', 'Paid'),
            ('cancelled', 'Cancelled'),
            ('shipped', 'Shipped'),
        ],
        default='pending',
    )
    # El total se calculará y almacenará al crear la cotización
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta: # Añadir Meta si no la tienes
        verbose_name = "Cotización / Pedido"
        verbose_name_plural = "Cotizaciones / Pedidos"
        ordering = ['-created_at']

    def get_customer_identifier(self):
        if self.customer_name:
            return f"{self.customer_name} (Invitado)"
        if self.customer_email:
            return f"{self.customer_email} (Invitado)"
        if self.user:
            return self.user.email # O self.user.username
        return f"Anónimo (ID: {self.pk})"

    @property
    def subtotal(self):
        """Calcula el subtotal de los items antes de cualquier descuento de cupón."""
        return sum(item.subtotal for item in self.items.all())

    def __str__(self):
        return f"Cotización #{self.pk} - {self.get_status_display()} para {self.get_customer_identifier()}"

class QuoteItem(models.Model):
    quote = models.ForeignKey(Quote, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT) # Usar PROTECT para no eliminar productos si están en una cotización/venta
    quantity = models.PositiveIntegerField(default=1)
    price_at_quote = models.DecimalField(max_digits=10, decimal_places=2)
    cost_at_quote = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    @property
    def subtotal(self) -> Decimal:
        return self.price_at_quote * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Quote {self.quote.id}"