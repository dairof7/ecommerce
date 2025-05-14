# sales/models.py
from django.db import models
from products.models import Category, Subcategory, Product

class Discount(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name='discounts_category')  # Cambiado
    subcategory = models.ForeignKey(Subcategory, on_delete=models.CASCADE, null=True, blank=True, related_name='discounts_subcategory')  # Cambiado
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True, related_name='discounts')  # Cambiado
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    def __str__(self):
        return f"Discount: {self.percentage}%"