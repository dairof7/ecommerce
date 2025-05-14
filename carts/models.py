from django.db import models
from django.contrib.auth import get_user_model
from products.models import Product

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
        price_after_discount = self.product.sale_price * (1 - self.product.discount / 100)
        print('p' * 20)
        print(price_after_discount * self.quantity)
        return price_after_discount * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Cart {self.cart.id}"

class Quote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quotes')
    # Mantener el enlace al carrito es opcional, pero puede dar contexto de qué carrito lo generó
    # Si el carrito original se elimina, este enlace podría romperse, considera si es necesario.
    # Por ahora, lo mantendremos.
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

    def __str__(self):
        return f"Quote {self.pk} - {self.status} for {self.user.username}"

class QuoteItem(models.Model):
    quote = models.ForeignKey(Quote, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT) # Usar PROTECT para no eliminar productos si están en una cotización/venta
    quantity = models.PositiveIntegerField(default=1)
    price_at_quote = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.quantity * self.price_at_quote

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Quote {self.quote.id}"