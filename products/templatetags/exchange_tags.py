from django import template
from django.core.cache import cache
from decimal import Decimal
import requests

register = template.Library()

@register.simple_tag
def current_exchange_rate():
    rate = cache.get('current_usd_cop_rate')
    if not rate:
        try:
            response = requests.get('https://open.er-api.com/v6/latest/USD', timeout=5)
            if response.status_code == 200:
                cop_rate = response.json().get('rates', {}).get('COP')
                if cop_rate:
                    # Guardar el valor oficial sin margen adicional
                    rate = Decimal(str(cop_rate))
                    # Guardar en caché por 24 horas (86400 segundos)
                    cache.set('current_usd_cop_rate', rate, timeout=86400)
        except Exception:
            pass

    if rate:
        # Formatear el número para que se vea bien, ej: 4,120.00
        return f"{rate:,.2f}"
    return "No disp."
