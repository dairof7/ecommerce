# carts/views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Cart, CartItem, Quote, QuoteItem
from products.models import Product
from .serializers import CartSerializer, CartItemSerializer, QuoteSerializer, QuoteItemSerializer # Importa QuoteItemSerializer
from rest_framework.permissions import IsAuthenticated
from django.db import transaction # Importar para transacciones atómicas
from decimal import Decimal
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]


    @extend_schema(
        parameters=[
            OpenApiParameter(name='id', description='A unique integer value identifying this cart.', required=True, type=OpenApiTypes.INT, location=OpenApiParameter.PATH)
        ]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        parameters=[
            OpenApiParameter(name='id', description='A unique integer value identifying this cart.', required=True, type=OpenApiTypes.INT, location=OpenApiParameter.PATH)
        ]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    @extend_schema(
        parameters=[
            OpenApiParameter(name='id', description='A unique integer value identifying this cart.', required=True, type=OpenApiTypes.INT, location=OpenApiParameter.PATH)
        ]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
    @extend_schema(
        parameters=[
            OpenApiParameter(name='id', description='A unique integer value identifying this cart.', required=True, type=OpenApiTypes.INT, location=OpenApiParameter.PATH)
        ]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)



    def get_queryset(self):
        """
        Retorna el carrito del usuario actual. Si el usuario no tiene carrito, crea uno.
        Usamos OneToOneField, así que get_or_create con filter es seguro.
        """
        user = self.request.user
        # Usamos OneToOneField, así que get_or_create es el método directo y asegura unicidad.
        cart, created = Cart.objects.get_or_create(user=user)
        # Devolvemos un queryset que contiene solo el carrito del usuario para que el ViewSet funcione
        return Cart.objects.filter(user=user) # Filtrar por usuario para asegurar el carrito correcto

    # Lista el carrito del usuario (GET /api/carts/)
    def list(self, request, *args, **kwargs):
        # get_queryset ya obtiene o crea el carrito
        cart = self.get_queryset().first()
        if not cart:
            # Esto solo ocurriría si get_queryset no pudiera obtener/crear, improbable con OneToOne
            return Response({"error": "Could not retrieve or create user cart."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    # Recupera un carrito específico (no necesario con OneToOne para el usuario actual)
    # def retrieve(self, request, pk=None):
    #     # Con OneToOne, el PK del carrito no es relevante para obtener el carrito del usuario actual
    #     # Podrías redefinir esto si quieres que admins puedan ver otros carritos por PK
    #     return super().retrieve(request, *args, **kwargs)


    @action(detail=False, methods=['post']) # Cambiamos a detail=False para operar en el carrito del usuario directamente
    def add_item(self, request):
        """
        Agrega o actualiza un producto en el carrito del usuario autenticado.
        Requiere 'product_id' y 'quantity' en el cuerpo de la solicitud.
        """
        cart = self.get_queryset().first() # Obtenemos el carrito del usuario autenticado

        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 0)) # Cantidad esperada

        if quantity <= 0:
            return Response({"error": "Quantity must be positive."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_400_BAD_REQUEST)

        # Validar stock antes de añadir/actualizar en el carrito
        # Si el item ya existe, sumamos la cantidad existente a la nueva cantidad para la validación
        existing_item = cart.items.filter(product=product).first()
        total_quantity_requested = quantity + (existing_item.quantity if existing_item else 0)

        if product.stock < total_quantity_requested:
            return Response({"error": f"Insufficient stock.  Only {product.stock} available for {product.name} (already in cart: {existing_item.quantity if existing_item else 0})."}, status=status.HTTP_400_BAD_REQUEST)

        # Usamos get_or_create para manejar si el item ya está en el carrito
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={'quantity': quantity})
        if not created:
            cart_item.quantity = total_quantity_requested # Actualiza la cantidad total
            cart_item.save()

        serializer = CartItemSerializer(cart_item)
        return Response(serializer.data, status=status.HTTP_200_OK) # Usamos 200 OK para actualizar, 201 Created para crear

    @action(detail=False, methods=['delete'], url_path=r'remove_item/(?P<item_id>\d+)')
    def remove_item(self, request, item_id=None):
        """
        Elimina un item específico del carrito del usuario autenticado.
        Requiere el 'item_id' en la URL.
        """
        cart = self.get_queryset().first() # Obtenemos el carrito del usuario autenticado
        if not cart:
            return Response({"error": "User does not have a cart."}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Aseguramos que el item pertenece al carrito del usuario autenticado
            cart_item = CartItem.objects.get(cart=cart, pk=item_id)
        except CartItem.DoesNotExist:
            return Response({"error": "Item not found in cart or does not belong to this cart."}, status=status.HTTP_404_NOT_FOUND)

        cart_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post']) # Cambiamos a detail=False
    def create_quote(self, request):
        """
        Crea una cotización a partir del carrito actual del usuario autenticado.
        Valida stock, crea QuoteItems, calcula total, descuenta stock y vacía el carrito.
        """
        cart = self.get_queryset().first() # Obtenemos el carrito del usuario autenticado
        if not cart:
            return Response({"error": "User does not have a cart or cart is empty."}, status=status.HTTP_404_NOT_FOUND)

        cart_items = cart.items.all()

        if not cart_items.exists():
            return Response({"error": "Cart is empty. Cannot create a quote."}, status=status.HTTP_400_BAD_REQUEST)

        # Usamos una transacción atómica para asegurar que si algo falla,
        # todos los cambios (creación de quote/items, descuento de stock) se revierten.
        try:
            with transaction.atomic():
                # 1. Crear la cotización (estado inicial 'pending', total 0 por ahora)
                # Se asocia al usuario y opcionalmente al carrito que la originó.
                quote = Quote.objects.create(
                    user=request.user,
                    cart=cart, # Guardamos la referencia al carrito que originó la cotización
                    status='pending',
                    total=Decimal('0.00') # Inicializar con Decimal
                )

                # 2. Crear QuoteItems y calcular el total
                quote_total = Decimal('0.00') # Usar Decimal para el total
                quote_items_to_create = []

                for item in cart_items:
                    product = item.product

                    # Usar la propiedad final_sale_price del modelo Product
                    price_at_quote = product.final_sale_price 

                    quote_item_instance = QuoteItem(
                        quote=quote,
                        product=product,
                        quantity=item.quantity,
                        price_at_quote=price_at_quote # Este es el precio con todos los descuentos aplicados
                    )
                    quote_items_to_create.append(quote_item_instance)
                    quote_total += quote_item_instance.subtotal # subtotal usará este price_at_quote

                    quote_items_to_create.append(quote_item_instance)
                    
                    # Sumar al total usando la propiedad subtotal del QuoteItem (que usa price_at_quote)
                    # Esto requiere que la instancia tenga price_at_quote seteado.
                    quote_total += quote_item_instance.subtotal # Llama a la propiedad @property subtotal

                # 3. Bulk create QuoteItems para eficiencia (esto los guarda en la BD)
                QuoteItem.objects.bulk_create(quote_items_to_create)

                # 4. Actualizar el total en la cotización
                quote.total = quote_total
                quote.save() # Guardar la cotización con el total actualizado

                # 5. Vaciar el carrito después de generar la cotización
                cart_items.delete()

        except ValueError as e: # Capturar el ValueError que levantamos antes
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e: # Capturar cualquier otra excepción durante la transacción
            # Log el error real para depuración interna
            print(f"Error creating quote: {str(e)}") # Considera usar logging.error()
            return Response({"error": "An unexpected error occurred while creating the quote."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Si la transacción fue exitosa, serializar y retornar la cotización
        # El QuoteSerializer debería tener `items = QuoteItemSerializer(many=True, read_only=True)`
        # para que los items recién creados se incluyan.
        serializer = QuoteSerializer(quote)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class QuoteViewSet(viewsets.ModelViewSet):
    serializer_class = QuoteSerializer
    permission_classes = [IsAuthenticated]




    @extend_schema(
        parameters=[
            OpenApiParameter(name='id', description='A unique integer value identifying this cart.', required=True, type=OpenApiTypes.INT, location=OpenApiParameter.PATH)
        ]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        parameters=[
            OpenApiParameter(name='id', description='A unique integer value identifying this cart.', required=True, type=OpenApiTypes.INT, location=OpenApiParameter.PATH)
        ]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    @extend_schema(
        parameters=[
            OpenApiParameter(name='id', description='A unique integer value identifying this cart.', required=True, type=OpenApiTypes.INT, location=OpenApiParameter.PATH)
        ]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
    @extend_schema(
        parameters=[
            OpenApiParameter(name='id', description='A unique integer value identifying this cart.', required=True, type=OpenApiTypes.INT, location=OpenApiParameter.PATH)
        ]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)



    def get_queryset(self):
        """
        Permite a los usuarios ver solo sus propias cotizaciones.
        Permite a los administradores ver todas las cotizaciones.
        Prefetch related items for efficiency.
        """
        queryset = Quote.objects.all().select_related('user').prefetch_related('items') # Mejora el rendimiento

        if self.request.user.is_staff:
            # Los administradores pueden ver todas las cotizaciones
            return queryset.order_by('-created_at') # Ordenar por fecha de creación descendente
        else:
            # Los usuarios normales solo ven las cotizaciones asociadas a ellos
            return queryset.filter(user=self.request.user).order_by('-created_at')

    @action(detail=True, methods=['post'])
    def finalize_sale(self, request, pk=None):
        """
        Finaliza la venta de una cotización (cambia el estado a 'paid').
        Solo accesible para administradores.
        """
        if not self.request.user.is_staff:
            return Response({"error": "Unauthorized. Only administrators can finalize sales."}, status=status.HTTP_403_FORBIDDEN)

        try:
            # Usamos get_object() que ya aplica los permisos (aunque para admin permite todo)
            # Aseguramos que obtenemos la cotización correcta
            quote = self.get_object()
        except Quote.DoesNotExist:
            return Response({"error": "Quote not found."}, status=status.HTTP_404_NOT_FOUND)

        # Validar el estado actual de la cotización
        if quote.status != 'pending':
            return Response({"error": f"Quote is not pending. Current status: {quote.status}"}, status=status.HTTP_400_BAD_REQUEST)

        # Usamos una transacción atómica para la actualización del estado
        with transaction.atomic():
            for item in quote.items.all(): # Iterar sobre los QuoteItems de la cotización
                product = Product.objects.select_for_update().get(pk=item.product.pk) # Bloqueo para concurrencia
                if product.stock < item.quantity:
                    # No hay suficiente stock para este item.
                    # Revertir la transacción y devolver un error.
                    transaction.set_rollback(True) # Asegura que la transacción se revierte
                    return Response(
                        {"error": f"Insufficient stock to finalize sale for product '{product.name}'. Available: {product.stock}, Requested in quote: {item.quantity}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                # Si hay stock, descontarlo
                product.stock -= item.quantity
                product.save()
            quote.status = 'paid'
            quote.save()
            # Si necesitas hacer algo más al finalizar la venta (ej. generar factura, enviar correo)
            # agrégalo aquí dentro de la transacción.

        # No es necesario descontar stock aquí, se hizo en create_quote.
        # Si el stock solo se descuenta al finalizar la venta, mueve esa lógica aquí.
        # PERO, eso significa que el stock no está reservado durante el estado 'pending',
        # lo cual puede llevar a problemas de sobreventa. Descontar al crear la quote
        # (o al menos reservar de alguna forma) es mejor para control de inventario.

        serializer = QuoteSerializer(quote) # Serializar la cotización actualizada
        return Response({"message": f"Sale for quote {quote.pk} finalized successfully. Status changed to paid, 'quote': {serializer.data}"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def cancel_quote(self, request, pk=None):
        """
        Cancela una cotización y restaura el stock.
        Puede ser accesible para el usuario (si está pendiente) o para el admin.
        """
        # Quien puede cancelar? Usuario si está pendiente? Admin siempre?
        # Aquí permitiremos al admin cancelar cualquier cotización,
        # y al usuario cancelar sus propias cotizaciones si están pendientes.

        try:
            # get_object aplica el filtro por usuario si no es admin
            quote = self.get_object()
        except Quote.DoesNotExist:
            return Response({"error": "Quote not found."}, status=status.HTTP_404_NOT_FOUND)

        # Validar quién está cancelando y el estado
        if not self.request.user.is_staff and quote.user != self.request.user:
            return Response({"error": "Unauthorized to cancel this quote."}, status=status.HTTP_403_FORBIDDEN)

        if quote.status not in ['pending']: # Solo se pueden cancelar cotizaciones pendientes
            return Response({"error": f"Quote cannot be cancelled. Current status: {quote.status}"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Cambiar el estado a 'cancelled'
            quote.status = 'cancelled'
            quote.save()

            # Restaurar el stock que fue descontado al crear la cotización
            # Solo si el stock fue descontado al crear la cotización (como lo implementamos)
            for item in quote.items.all():
                product = item.product
                # Opcional: usar select_for_update() si hay mucha concurrencia en restaurar stock
                product.stock += item.quantity
                product.save()

        serializer = QuoteSerializer(quote)
        return Response({"message": f"Quote {quote.pk} cancelled successfully. Stock restored.", "quote": serializer.data}, status=status.HTTP_200_OK)