# carts/templatetags/currency_filters.py
from django import template
from django.contrib.humanize.templatetags.humanize import intcomma # Importa intcomma
from django.utils.safestring import mark_safe
from decimal import Decimal

register = template.Library()

@register.filter(name='currency')
def currency_format(value):
    """
    Formatea un valor numérico como moneda:
    - Sin decimales (redondeado).
    - Con puntos como separador de miles.
    - Con el símbolo '$' al principio.
    Ejemplo: 1250000.50 -> $1.250.001
    """
    try:
        # Convertir a Decimal para un redondeo preciso
        value = Decimal(value)
        # Redondear al entero más cercano
        rounded_value = round(value)
        # Convertir a entero para intcomma
        int_value = int(rounded_value)
        # Aplicar separador de miles
        formatted_value = intcomma(int_value, use_l10n=False) # use_l10n=False para forzar el THOUSAND_SEPARATOR de settings
        
        # Añadir el símbolo de moneda
        return f"${formatted_value}"
    except (ValueError, TypeError):
        return value # Devolver el valor original si no se puede formatear

# Opcional: registrar la app 'humanize'
# Si solo quieres usar |floatformat:0|intcomma, necesitarías tener 'django.contrib.humanize'
# en tus INSTALLED_APPS en settings.py.
# Pero el filtro personalizado de arriba es más robusto y no requiere esa app.