# carts/admin.py
from django.contrib import admin
from .models import Cart, CartItem, Quote, QuoteItem # Importa QuoteItem
from django.urls import path
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import TruncMonth
from django.db.models import Sum, F, DecimalField

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0 # Mostrar 0 campos vacíos por defecto, solo mostrar los existentes
    readonly_fields = ('subtotal',) # Mostrar el subtotal pero no editarlo


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id','user', 'created_at', 'updated_at')
    list_filter = ('user',)
    search_fields = ('user__username',)
    inlines = [CartItemInline]
    readonly_fields = ('created_at', 'updated_at')

class QuoteItemInline(admin.TabularInline):
    model = QuoteItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price_at_quote', 'subtotal') # Los items de la cotización son de solo lectura
    can_delete = False
    def has_add_permission(self, request, obj=None):
        return False
@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ('id','user','customer_name', 'customer_email', 'customer_phone', 'status', 'total','created_at') # Mostrar user en lugar de cart
    list_filter = ('status', 'created_at', 'user')
    search_fields = ('user__username',) # Buscar por nombre de usuario
    readonly_fields = ('user', 'cart', 'created_at', 'updated_at', 'total') # Campos de solo lectura
    inlines = [QuoteItemInline] # Mostrar los items de la cotización

    fieldsets = (
        (None, {
            'fields': ('user','customer_name','customer_email','customer_document','customer_phone', 'cart', 'created_at', 'updated_at', 'status', 'total')
        }),
        # Los items se mostrarán a través del inline
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('sales-dashboard/', self.admin_site.admin_view(self.sales_dashboard_view), name='carts_quote_sales_dashboard')
        ]
        return custom_urls + urls

    def sales_dashboard_view(self, request):
        current_time = timezone.now()
        
        # Definir el número de items a mostrar en los rankings "Top"
        TOP_N = 10
        
        # 1. Top N Best-Selling & Most Profitable Products (Last 4 Months)
        four_months_ago_total = current_time - timedelta(days=120)

        base_query = QuoteItem.objects.filter(
            quote__status__in=['paid', 'shipped'],
            quote__created_at__gte=four_months_ago_total,
            product__purchase_price__isnull=False
        ).values('product__name').annotate(
            total_sold=Sum('quantity'),
            total_profit=Sum(
                (F('price_at_quote') - F('product__purchase_price')) * F('quantity'),
                output_field=DecimalField()
            )
        )

        top_selling_products = base_query.order_by('-total_sold')[:TOP_N]
        top_profit_products = base_query.order_by('-total_profit')[:TOP_N]

        # 2. Total Sales & Category Sales (Last 4 Months)
        # --- Generate labels and date range for the last 4 months ---
        months_to_show = 4
        today = current_time.date()
        month_labels = []
        first_day_of_current_month = today.replace(day=1)

        start_date_year = first_day_of_current_month.year
        start_date_month = first_day_of_current_month.month - (months_to_show - 1)
        while start_date_month <= 0:
            start_date_month += 12
            start_date_year -= 1
        four_months_ago = first_day_of_current_month.replace(year=start_date_year, month=start_date_month)

        temp_date = four_months_ago
        for _ in range(months_to_show):
            month_labels.append(temp_date.strftime("%b %Y"))
            next_month = temp_date.month + 1
            next_year = temp_date.year
            if next_month > 12:
                next_month = 1
                next_year += 1
            temp_date = temp_date.replace(year=next_year, month=next_month)

        # --- Prepare data for "Total Sales" chart ---
        sales_data_dict = {label: 0 for label in month_labels}
        sales_last_4_months = Quote.objects.filter(
            status__in=['paid', 'shipped'],
            created_at__gte=four_months_ago
        ).annotate(month_year=TruncMonth('created_at')).values('month_year').annotate(total_sales=Sum('total'))

        for sale in sales_last_4_months:
            label = sale['month_year'].strftime("%b %Y")
            if label in sales_data_dict:
                sales_data_dict[label] = float(sale['total_sales'])
        sales_chart_data = {"labels": list(sales_data_dict.keys()), "data": list(sales_data_dict.values())}

        # --- Prepare data for "Sales by Category" chart ---
        sales_by_cat_month = QuoteItem.objects.filter(
            quote__status__in=['paid', 'shipped'],
            quote__created_at__gte=four_months_ago
        ).annotate(
            month_year=TruncMonth('quote__created_at')
        ).values(
            'month_year', 'product__category__name'
        ).annotate(total_sales=Sum(F('quantity') * F('price_at_quote'))).order_by('month_year')

        all_categories = sorted(list(set(d['product__category__name'] for d in sales_by_cat_month if d.get('product__category__name'))))
        category_sales_data = {cat_name: {m_label: 0 for m_label in month_labels} for cat_name in all_categories}

        for item in sales_by_cat_month:
            category_name = item.get('product__category__name')
            if not category_name: continue
            month_label = item['month_year'].strftime("%b %Y")
            if month_label in month_labels and category_name in category_sales_data:
                category_sales_data[category_name][month_label] = float(item['total_sales'])

        # Paleta de colores más oscura
        category_colors = [
            'rgba(0, 128, 128, 0.7)',   # Dark Teal
            'rgba(70, 130, 180, 0.7)',  # Steel Blue
            'rgba(47, 79, 79, 0.7)',    # Dark Slate Gray
            'rgba(75, 0, 130, 0.7)',    # Indigo
            'rgba(128, 0, 0, 0.7)',     # Maroon
            'rgba(85, 107, 47, 0.7)',   # Dark Olive Green
            'rgba(139, 69, 19, 0.7)',   # Saddle Brown
            'rgba(139, 0, 139, 0.7)',   # Dark Magenta
            'rgba(25, 25, 112, 0.7)',   # Midnight Blue
            'rgba(72, 61, 139, 0.7)'    # Dark Slate Blue
        ]
        category_chart_datasets = []
        for i, cat_name in enumerate(all_categories):
            dataset = {
                'label': cat_name,
                'data': [category_sales_data[cat_name][m_label] for m_label in month_labels],
                'backgroundColor': category_colors[i % len(category_colors)],
            }
            category_chart_datasets.append(dataset)

        category_sales_chart_data = {
            'labels': month_labels,
            'datasets': category_chart_datasets
        }

        context = dict(
           self.admin_site.each_context(request),
           title="Dashboard de Ventas",
           top_selling_products=list(top_selling_products),
           top_profit_products=list(top_profit_products),
           sales_chart_data=sales_chart_data,
           category_sales_chart_data=category_sales_chart_data,
        )
        return render(request, "admin/sales_dashboard.html", context)

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('id','cart', 'product', 'quantity', 'subtotal') # Mostrar subtotal
    list_filter = ('cart__user', 'product') # Filtrar por usuario del carrito y producto
    search_fields = ('cart__user__username', 'product__name')
    readonly_fields = ('subtotal',)

# Registrar QuoteItem (aunque se verá principalmente como inline en Quote)
@admin.register(QuoteItem)
class QuoteItemAdmin(admin.ModelAdmin):
    list_display = ('id','quote', 'product', 'quantity', 'price_at_quote', 'subtotal')
    list_filter = ('quote__user', 'product', 'quote__status') # Filtrar por usuario de la cotización, producto y estado de la cotización
    search_fields = ('quote__user__username', 'product__name', 'quote__id')
    readonly_fields = ('quote', 'product', 'quantity', 'price_at_quote', 'subtotal')