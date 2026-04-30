# carts/admin.py
from django.contrib import admin
from .models import Cart, CartItem, Quote, QuoteItem, Coupon
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from products.models import Product
from datetime import timedelta
from decimal import Decimal
from django.db.models.functions import TruncMonth, Coalesce
from django.db.models import Sum, F, DecimalField, OuterRef, Subquery
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML, CSS
from django.utils.html import format_html
from .tasks import get_shop_info

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0 # Mostrar 0 campos vacíos por defecto, solo mostrar los existentes
    readonly_fields = ('subtotal',) # Mostrar el subtotal pero no editarlo


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id','user', 'coupon', 'created_at', 'updated_at')
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
    list_display = ('id', 'user', 'customer_name', 'customer_email', 'status', 'total', 'created_at', 'receipt_actions', 'quote_actions')
    list_filter = ('status', 'created_at', 'user')
    search_fields = ('user__username', 'customer_name', 'customer_email', 'coupon__code')
    readonly_fields = ('user', 'cart', 'created_at', 'updated_at', 'total', 'coupon_discount')
    inlines = [QuoteItemInline] # Mostrar los items de la cotización
    
    # Añadimos el campo a la tupla de ordenación para evitar errores
    ordering = ('-created_at',)

    fieldsets = (
        (None, {
            'fields': ('user', 'customer_name', 'customer_email', 'customer_document', 'customer_phone', 'cart', 'created_at', 'updated_at', 'status', 'coupon', 'coupon_discount', 'total')
        }),
        # Los items se mostrarán a través del inline
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('pos/', self.admin_site.admin_view(self.pos_view), name='carts_quote_pos'),
            path('sales-dashboard/', self.admin_site.admin_view(self.sales_dashboard_view), name='carts_quote_sales_dashboard'),
            path('<int:quote_id>/receipt/', self.admin_site.admin_view(self.view_receipt_pdf), name='view_receipt_pdf'),
            path('<int:quote_id>/mark-paid/', self.admin_site.admin_view(self.mark_quote_paid), name='quote_mark_paid'),
            path('<int:quote_id>/mark-shipped/', self.admin_site.admin_view(self.mark_quote_shipped), name='quote_mark_shipped'),
            path('<int:quote_id>/cancel/', self.admin_site.admin_view(self.cancel_quote), name='quote_cancel'),
        ]
        return custom_urls + urls

    def view_receipt_pdf(self, request, quote_id):
        """
        Genera un PDF de 58mm con altura dinámica basada en el contenido
        para simular impresión continua.
        """
        try:
            quote = self.get_queryset(request).get(id=quote_id)
        except Quote.DoesNotExist:
            return HttpResponse("Este pedido no existe.", status=404)

        shop_info = get_shop_info()
        # Lógica de nombre del cliente (existente)
        if quote.user:
            customer_name = quote.user.get_full_name() or quote.user.username
        else:
            customer_name = quote.customer_name or 'Cliente'
        
        customer_info = {'name': customer_name}

        # --- LÓGICA DE ALTURA DINÁMICA ---
        # 1. Definimos una altura base para cabecera, footer y totales (ajustar según tu diseño)
        base_height_mm = 90 
        
        # 2. Definimos altura estimada por ítem (considerando saltos de línea en descripciones largas)
        item_height_mm = 12 
        
        # 3. Contamos los ítems (usando la relación inversa quoteitem_set o document.items)
        # Nota: Asegúrate de que 'items' es el related_name correcto, o usa quoteitem_set
        num_items = quote.items.count()
        
        # 4. Calculamos altura total
        total_height = base_height_mm + (num_items * item_height_mm)
        
        # Aseguramos un mínimo razonable (por si hay 0 items o es muy corto)
        if total_height < 60:
            total_height = 60

        context = {
            'document': quote,
            'shop_info': shop_info,
            'customer_info': customer_info,
        }

        html_string = render_to_string('carts/pdf/receipt_58mm_template.html', context)
        
        # --- CSS DINÁMICO ---
        # Inyectamos la altura calculada en la directiva @page
        # Importante: margin: 0mm para que el body controle los márgenes internos
        css_string = f'@page {{ size: 58mm {total_height}mm; margin: 0mm; }}'
        
        css = CSS(string=css_string)
        
        pdf_file = HTML(string=html_string).write_pdf(stylesheets=[css])

        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="recibo_58mm_{quote.id}.pdf"'
        return response
    
    def receipt_actions(self, obj):
        # Solo muestra el botón si el estado es 'paid' o 'shipped'
        if obj.status in ['pending', 'paid', 'shipped']:
            url = reverse('admin:view_receipt_pdf', args=[obj.id])
            return format_html('<a class="button" href="{}" target="_blank">Ver Recibo</a>', url)
        return "N/A"
    receipt_actions.short_description = 'Recibo (58mm)'
    receipt_actions.allow_tags = True
    
    def quote_actions(self, obj):
        actions = []
        if obj.status == 'pending':
            actions.append(f'<a class="button" style="background-color: #28a745; margin-right: 5px;" href="{reverse("admin:quote_mark_paid", args=[obj.id])}">Marcar Pagado</a>')
            actions.append(f'<a class="button" style="background-color: #dc3545;" href="{reverse("admin:quote_cancel", args=[obj.id])}">Cancelar</a>')
        elif obj.status == 'paid':
            actions.append(f'<a class="button" style="background-color: #007bff; margin-right: 5px;" href="{reverse("admin:quote_mark_shipped", args=[obj.id])}">Marcar Enviado</a>')
            actions.append(f'<a class="button" style="background-color: #dc3545;" href="{reverse("admin:quote_cancel", args=[obj.id])}">Cancelar</a>')
        return format_html("".join(actions))
    quote_actions.short_description = 'Acciones Rápidas'
    quote_actions.allow_tags = True

    def mark_quote_paid(self, request, quote_id):
        quote = self.get_object(request, str(quote_id))
        if quote and quote.status == 'pending':
            try:
                with transaction.atomic():
                    for item in quote.items.all():
                        product = Product.objects.select_for_update().get(pk=item.product.pk)
                        if product.stock < item.quantity:
                            raise ValueError(f"Stock insuficiente para '{product.name}'. Disponible: {product.stock}, Solicitado: {item.quantity}")
                        product.stock -= item.quantity
                        product.save()

                    if quote.coupon:
                        Coupon.objects.filter(pk=quote.coupon.pk).update(uses_count=F('uses_count') + 1)

                    quote.status = 'paid'
                    quote.save()
                    self.message_user(request, f"Cotización #{quote.id} marcada como Pagada.", messages.SUCCESS)
            except ValueError as e:
                self.message_user(request, str(e), messages.ERROR)
            except Exception as e:
                self.message_user(request, "Error inesperado al marcar como pagada.", messages.ERROR)
        return redirect('admin:carts_quote_changelist')

    def mark_quote_shipped(self, request, quote_id):
        quote = self.get_object(request, str(quote_id))
        if quote and quote.status == 'paid':
            quote.status = 'shipped'
            quote.save()
            self.message_user(request, f"Cotización #{quote.id} marcada como Enviada.", messages.SUCCESS)
        return redirect('admin:carts_quote_changelist')

    def cancel_quote(self, request, quote_id):
        quote = self.get_object(request, str(quote_id))
        if quote and quote.status in ['pending', 'paid']:
            previous_status = quote.status
            try:
                with transaction.atomic():
                    quote.status = 'cancelled'
                    quote.save()

                    if previous_status == 'paid':
                        for item in quote.items.all():
                            product = Product.objects.select_for_update().get(pk=item.product.pk)
                            product.stock += item.quantity
                            product.save()
                        
                        if quote.coupon:
                            Coupon.objects.filter(pk=quote.coupon.pk, uses_count__gt=0).update(uses_count=F('uses_count') - 1)
                            
                    self.message_user(request, f"Cotización #{quote.id} cancelada exitosamente." + (" Stock restaurado." if previous_status == 'paid' else ""), messages.WARNING)
            except Exception as e:
                self.message_user(request, "Error al cancelar la cotización.", messages.ERROR)
        return redirect('admin:carts_quote_changelist')

    def pos_view(self, request):
        context = dict(
           self.admin_site.each_context(request),
           title="Punto de Venta (POS)"
        )
        return render(request, "admin/carts/pos.html", context)

    # --- DASHBOARD DE VENTAS (sin cambios) ---
    # ... (el resto del código del dashboard se mantiene igual)


    def sales_dashboard_view(self, request):
        import calendar
        from datetime import datetime
        current_time = timezone.now()
        
        # Definir el número de items a mostrar en los rankings "Top"
        TOP_N = 10
        
        # Determine date range (default: last 6 months)
        end_date_default = current_time.date()
        m = end_date_default.month - 5
        y = end_date_default.year
        while m <= 0:
            m += 12
            y -= 1
        start_date_default = end_date_default.replace(year=y, month=m, day=1)

        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')

        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                start_date = start_date_default
                end_date = end_date_default
        else:
            start_date = start_date_default
            end_date = end_date_default

        if start_date > end_date:
            start_date, end_date = end_date, start_date

        start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
        end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))

        # 1. Top N Best-Selling & Most Profitable Products
        base_query = QuoteItem.objects.filter(
            quote__status__in=['paid', 'shipped'],
            quote__created_at__gte=start_datetime,
            quote__created_at__lte=end_datetime,
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

        # 2. Total Sales & Category Sales
        # --- Generate labels and date range ---
        month_labels = []
        temp_date = start_date.replace(day=1)
        end_month_first_day = end_date.replace(day=1)

        while temp_date <= end_month_first_day:
            month_labels.append(temp_date.strftime("%b %Y"))
            next_month = temp_date.month + 1
            next_year = temp_date.year
            if next_month > 12:
                next_month = 1
                next_year += 1
            temp_date = temp_date.replace(year=next_year, month=next_month)

        if not month_labels:
            month_labels.append(start_date.strftime("%b %Y"))

        # --- Prepare data for "Total Sales" and "Monthly Profit" chart ---
        sales_data_dict = {label: 0 for label in month_labels}
        profit_data_dict = {label: 0 for label in month_labels}

        cost_subquery = QuoteItem.objects.filter(
            quote=OuterRef('pk')
        ).values('quote').annotate(
            total_cost=Sum(F('quantity') * Coalesce(F('product__purchase_price'), Decimal('0.0')), output_field=DecimalField())
        ).values('total_cost')

        sales_in_range = Quote.objects.filter(
            status__in=['paid', 'shipped'],
            created_at__gte=start_datetime,
            created_at__lte=end_datetime
        ).annotate(
            month_year=TruncMonth('created_at'),
            quote_cost=Subquery(cost_subquery, output_field=DecimalField())
        ).values('month_year').annotate(
            total_sales=Sum('total', output_field=DecimalField()),
            total_cost=Sum('quote_cost', output_field=DecimalField())
        )

        for sale in sales_in_range:
            if sale['month_year']:
                label = sale['month_year'].strftime("%b %Y")
                if label in sales_data_dict:
                    sales_val = float(sale['total_sales'] or 0)
                    cost_val = float(sale['total_cost'] or 0)
                    sales_data_dict[label] = sales_val
                    profit_data_dict[label] = sales_val - cost_val

        sales_chart_data = {"labels": list(sales_data_dict.keys()), "data": list(sales_data_dict.values())}
        profit_chart_data = {"labels": list(profit_data_dict.keys()), "data": list(profit_data_dict.values())}

        # --- Prepare data for "Sales by Category" chart ---
        sales_by_cat_month = QuoteItem.objects.filter(
            quote__status__in=['paid', 'shipped'],
            quote__created_at__gte=start_datetime,
            quote__created_at__lte=end_datetime
        ).annotate(
            month_year=TruncMonth('quote__created_at')
        ).values(
            'month_year', 'product__category__name'
        ).annotate(total_sales=Sum(F('quantity') * F('price_at_quote'))).order_by('month_year')

        all_categories = sorted(list(set(d['product__category__name'] for d in sales_by_cat_month if d.get('product__category__name'))))
        category_sales_data = {cat_name: {m_label: 0 for m_label in month_labels} for cat_name in all_categories}

        for item in sales_by_cat_month:
            category_name = item.get('product__category__name')
            if not category_name or not item['month_year']: continue
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
           profit_chart_data=profit_chart_data,
           category_sales_chart_data=category_sales_chart_data,
           start_date=start_date.strftime('%Y-%m-%d'),
           end_date=end_date.strftime('%Y-%m-%d')
        )
        return render(request, "admin/sales_dashboard.html", context)



@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'min_purchase_amount', 'uses_limit', 'uses_count','is_active','valid_from', 'valid_to')
    list_filter = ('is_active', 'discount_type', 'valid_to')
    search_fields = ('code',)
    readonly_fields = ('uses_count',)
    fieldsets = (
        (None, {
            'fields': ('code', 'is_active')
        }),
        ('Validez', {
            'fields': ('valid_from', 'valid_to')
        }),
        ('Reglas de Descuento', {
            'fields': ('discount_type', 'discount_value', 'max_discount_amount', 'min_purchase_amount')
        }),
        ('Límites de Uso', {
            'fields': ('uses_limit', 'uses_count')
        }),
    )
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