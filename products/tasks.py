import requests
from celery import shared_task
from django.db.models import F
from decimal import Decimal
from django.core.cache import cache
from .models import Product
import logging

logger = logging.getLogger(__name__)

@shared_task
def update_cop_costs_from_usd():
    """
    Obtiene la tasa de cambio actual USD a COP y actualiza 
    el reference_cop_cost de los productos que tienen reference_usd_cost.
    """
    try:
        response = requests.get('https://open.er-api.com/v6/latest/USD')
        response.raise_for_status()
        data = response.json()
        
        cop_rate = data.get('rates', {}).get('COP')
        
        if not cop_rate:
            logger.error("No se pudo obtener la tasa COP desde la API de tipo de cambio.")
            return "Falló la obtención de la tasa COP."
            
        # Agregamos 40 pesos (margen de tarjetas de crédito) al valor oficial
        cop_rate_decimal = Decimal(str(cop_rate)) + Decimal('40.00')
        
        # Guardar en caché para mostrarlo rápido en el Admin sin consultar BD ni API
        cache.set('current_usd_cop_rate', cop_rate_decimal, timeout=None)
        
        # Filtrar productos que tienen costo en USD configurado
        products_to_update = Product.objects.filter(reference_usd_cost__isnull=False)
        
        updated_count = 0
        for product in products_to_update:
            new_cop_cost = product.reference_usd_cost * cop_rate_decimal
            # Redondear a 2 decimales para almacenar en base de datos
            product.reference_cop_cost = new_cop_cost.quantize(Decimal('0.01'))
            product.save(update_fields=['reference_cop_cost'])
            updated_count += 1
            
        logger.info(f"Se actualizaron {updated_count} productos con la nueva tasa USD a COP: {cop_rate_decimal}")
        return f"Éxito: {updated_count} productos actualizados (Tasa: {cop_rate_decimal})"
        
    except requests.RequestException as e:
        logger.error(f"Error al conectar con la API de tipo de cambio: {e}")
        return f"Error de red: {e}"
    except Exception as e:
        logger.error(f"Error inesperado al actualizar costos COP: {e}")
        return f"Error: {e}"
