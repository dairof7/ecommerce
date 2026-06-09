from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.db import transaction
from .models import StockEntry
from products.models import Product
from decimal import Decimal

@receiver(post_save, sender=StockEntry)
def update_product_stock_on_stock_entry_save(sender, instance, created, **kwargs):
    """
    Actualiza el stock del producto cuando se crea una nueva StockEntry.
    """
    if created: # Solo actuar si la StockEntry es nueva
        with transaction.atomic():
            product_to_update = Product.objects.select_for_update().get(pk=instance.product.pk)
            
            old_stock = Decimal(product_to_update.stock)
            old_average = product_to_update.average_cost
            new_quantity = Decimal(instance.quantity)
            new_price = instance.purchase_price
            
            total_new_stock = old_stock + new_quantity
            
            if total_new_stock > 0:
                new_average = ((old_stock * old_average) + (new_quantity * new_price)) / total_new_stock
                product_to_update.average_cost = new_average
            
            # Actualizamos purchase_price como el "último" precio de compra
            product_to_update.purchase_price = new_price
            
            product_to_update.stock += instance.quantity
            product_to_update.save()

@receiver(pre_delete, sender=StockEntry)
def update_product_stock_on_stock_entry_delete(sender, instance, **kwargs):
    """
    Actualiza (RESTA) el stock del producto cuando se ELIMINA una StockEntry.
    'instance' aquí es la StockEntry que está a punto de ser eliminada.
    """
    # Es una buena práctica verificar si el producto aún existe,
    # aunque con ForeignKey(on_delete=models.CASCADE) para product en StockEntry,
    # si el producto se elimina, las StockEntry asociadas también se eliminarían (y esta señal se dispararía).
    # Sin embargo, si on_delete fuera SET_NULL o PROTECT para product, esta verificación sería más crítica.
    try:
        with transaction.atomic():
            # Obtenemos el producto asociado a la StockEntry que se va a eliminar
            product_to_update = Product.objects.select_for_update().get(pk=instance.product.pk)
            
            # Restamos la cantidad de la StockEntry que se está eliminando
            # Asegurarse de que el stock no se vuelva negativo si hay inconsistencias.
            # Esto podría indicar un problema en otro lugar si sucede.
            if product_to_update.stock >= instance.quantity:
                product_to_update.stock -= instance.quantity
            else:
                # Manejar el caso de stock inconsistente. Podrías:
                # 1. Poner el stock a 0.
                # 2. Lanzar un error (lo que podría detener la eliminación si no se maneja).
                # 3. Loguear una advertencia severa.
                # Por ahora, lo pondremos a 0 y dejaremos un comentario.
                print(f"ADVERTENCIA: Al eliminar StockEntry ID {instance.pk} para el producto '{product_to_update.name}', "
                      f"el stock del producto ({product_to_update.stock}) es menor que la cantidad de la entrada ({instance.quantity}). "
                      f"Estableciendo stock a 0.")
                product_to_update.stock = 0
            
            product_to_update.save()
    except Product.DoesNotExist:
        # El producto asociado ya no existe. No hay nada que actualizar.
        # Esto podría suceder si el producto se eliminó y la cascada aún no ha procesado esta StockEntry,
        # o si la relación ForeignKey tiene on_delete=SET_NULL y product_id es None.
        print(f"Advertencia: El producto asociado a StockEntry ID {instance.pk} no fue encontrado al intentar actualizar stock durante la eliminación.")
    except Exception as e:
        # Manejar otras posibles excepciones para que la eliminación no falle silenciosamente
        # o para loguear el error.
        print(f"Error al actualizar el stock del producto durante la eliminación de StockEntry ID {instance.pk}: {e}")
        # Considera si quieres que la eliminación falle si la actualización de stock falla.
        # Por defecto, si esta señal lanza una excepción no controlada, la operación de eliminación se detendrá.
        raise # Volver a lanzar la excepción para detener la eliminación si es crítico