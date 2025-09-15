from django.db import models
from django.contrib.auth import get_user_model
from products.models import Product
from decimal import Decimal

User = get_user_model()

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.user.username}"

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

    def __str__(self):
        return f"Cotización #{self.pk} - {self.get_status_display()} para {self.get_customer_identifier()}"

class QuoteItem(models.Model):
    quote = models.ForeignKey(Quote, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT) # Usar PROTECT para no eliminar productos si están en una cotización/venta
    quantity = models.PositiveIntegerField(default=1)
    price_at_quote = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self) -> Decimal:

        # Usa la propiedad final_sale_price del producto asociado
        return self.product.final_sale_price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Quote {self.quote.id}"