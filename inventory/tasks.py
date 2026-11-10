from celery import shared_task
from .models import DailyStockSnapshot
import logging

logger = logging.getLogger(__name__)

@shared_task
def take_daily_stock_snapshot():
    """
    Tarea periódica de Celery que registra la valoración diaria del inventario.
    Se ejecuta típicamente a medianoche o cuando sea invocada.
    """
    try:
        snapshot = DailyStockSnapshot.record_snapshot()
        logger.info(f"Snapshot de stock registrado exitosamente: {snapshot}")
        return {
            'date': str(snapshot.date),
            'total_stock_cost': float(snapshot.total_stock_cost),
            'total_stock_sale': float(snapshot.total_stock_sale),
            'total_transit_cost': float(snapshot.total_transit_cost),
            'total_units_stock': snapshot.total_units_stock,
            'total_units_transit': snapshot.total_units_transit,
        }
    except Exception as e:
        logger.error(f"Error al registrar snapshot de stock: {e}", exc_info=True)
        raise

