from django import template
from django.core.cache import cache
from decimal import Decimal

register = template.Library()

@register.simple_tag
def current_exchange_rate():
    rate = cache.get('current_usd_cop_rate')
    if rate:
        # Formatear el número para que se vea bien, ej: 4,120.00
        return f"{rate:,.2f}"
    return "No disp."
