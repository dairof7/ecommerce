from django.db import models
from products.models import Product
from decimal import Decimal

class StockEntry(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Stock Entry for {self.product.name} - {self.quantity}"


class DailyStockSnapshot(models.Model):
    date = models.DateField(unique=True, db_index=True)
    total_stock_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_stock_sale = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_stock_profit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_transit_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_units_stock = models.PositiveIntegerField(default=0)
    total_units_transit = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date']
        verbose_name = 'Snapshot Diario de Stock'
        verbose_name_plural = 'Snapshots Diarios de Stock'

    def __str__(self):
        return f"{self.date} - Costo: ${self.total_stock_cost:,.0f}"

    @classmethod
    def record_snapshot(cls, target_date=None):
        from django.utils import timezone
        from products.models import Product
        from django.db.models import Sum, F, DecimalField

        if target_date is None:
            target_date = timezone.now().date()

        stock_qs = Product.objects.filter(
            is_active=True,
            is_service=False,
            is_combo=False,
            stock__gt=0
        )
        stock_agg = stock_qs.aggregate(
            total_cost=Sum(F('stock') * F('average_cost'), output_field=DecimalField()),
            total_sale=Sum(F('stock') * F('sale_price'), output_field=DecimalField()),
            total_units=Sum('stock')
        )
        total_stock_cost = stock_agg['total_cost'] or Decimal('0.00')
        total_stock_sale = stock_agg['total_sale'] or Decimal('0.00')
        total_units_stock = stock_agg['total_units'] or 0
        total_stock_profit = total_stock_sale - total_stock_cost

        transit_qs = Product.objects.filter(
            is_active=True,
            is_service=False,
            is_combo=False,
            incoming_stock__gt=0
        )
        transit_agg = transit_qs.aggregate(
            total_transit_cost=Sum(F('incoming_stock') * F('average_cost'), output_field=DecimalField()),
            total_units=Sum('incoming_stock')
        )
        total_transit_cost = transit_agg['total_transit_cost'] or Decimal('0.00')
        total_units_transit = transit_agg['total_units'] or 0

        snapshot, _ = cls.objects.update_or_create(
            date=target_date,
            defaults={
                'total_stock_cost': total_stock_cost,
                'total_stock_sale': total_stock_sale,
                'total_stock_profit': total_stock_profit,
                'total_transit_cost': total_transit_cost,
                'total_units_stock': total_units_stock,
                'total_units_transit': total_units_transit,
            }
        )
        return snapshot
