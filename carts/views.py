# carts/views.py
from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Cart, CartItem, Quote, QuoteItem
from products.models import Product
from .serializers import CartSerializer, CartItemSerializer, QuoteSerializer, QuoteItemSerializer # Importa QuoteItemSerializer
from rest_framework.permissions import IsAuthenticated
from django.db import transaction # Importar para transacciones atómicas
from decimal import Decimal
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from .tasks import send_quote_pdf_email
from .tasks import send_invoice_pdf_email
User = get_user_model()


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


    @action(detail=False, methods=['post'], url_path='add-one')
    def add_one_to_cart(self, request):
        cart = self.get_queryset().first()
        if not cart:
            return Response({"error": "Carrito no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        try:
            product_id = int(request.data.get('product_id'))
        except (ValueError, TypeError, KeyError):
            return Response({"error": "product_id es requerido y debe ser un entero."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Producto no encontrado."}, status=status.HTTP_400_BAD_REQUEST)

        quantity_to_add = 1 # Siempre añadimos 1 unidad con este endpoint

        with transaction.atomic():
            cart_item, created = CartItem.objects.select_for_update().get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': 0} # Inicializa en 0 si es nuevo, luego se suma 1
            )

            current_qty_in_cart = cart_item.quantity
            new_total_quantity = current_qty_in_cart + quantity_to_add

            if product.stock < new_total_quantity:
                current_in_cart_msg = f" Ya tienes {cart_item.quantity} en el carrito." if cart_item.quantity > 0 else ""
                return Response(
                    {"error": f"Stock insuficiente para '{product.name}'. Disponible: {product.stock}. Intentaste añadir {quantity_to_add}.{current_in_cart_msg}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            cart_item.quantity = new_total_quantity
            cart_item.save()
        
        cart.refresh_from_db()
        serializer = self.get_serializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='add_items') # Cambiado a 'item' y espera product_id y quantity total
    def add_items_by_quantity(self, request):
        cart = self.get_queryset().first()
        if not cart:
            return Response({"error": "Carrito no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        try:
            product_id = int(request.data.get('product_id'))
            # Esta 'quantity' es la NUEVA CANTIDAD TOTAL deseada para el item
            quantity = int(request.data.get('quantity')) 
        except (ValueError, TypeError, KeyError):
            return Response({"error": "product_id y quantity son requeridos y deben ser enteros."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Producto no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        if quantity <= 0: # Si la nueva cantidad es 0 o menos, eliminar el item
            CartItem.objects.filter(cart=cart, product=product).delete()
            action_taken = "eliminado"
        else:
            # Validar stock para la nueva cantidad total
            current_item = CartItem.objects.filter(cart=cart, product=product).first()
            current_qty_in_cart = current_item.quantity if current_item else 0
            if product.stock < quantity + current_qty_in_cart:
                return Response(
                    {"error": f"Stock insuficiente para '{product.name}'. Disponible: {product.stock}. Solicitado total: {quantity}. Ya en carrito: {current_qty_in_cart}."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Actualiza o crea el item con la cantidad especificada
            cart_item, created = CartItem.objects.update_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity + current_qty_in_cart} # ESTABLECE la cantidad
            )
            action_taken = "actualizado" if not created else "añadido"

        # Devolver el carrito completo actualizado
        cart.refresh_from_db() # Para asegurar que cualquier cálculo en el modelo Cart se actualice
        serializer = self.get_serializer(cart) # Usa el serializer del ViewSet (CartSerializer)
        return Response(serializer.data, status=status.HTTP_200_OK)


    @action(detail=False, methods=['post']) # Cambiamos a detail=False para operar en el carrito del usuario directamente
    def add_item(self, request):
        """
        Agrega o actualiza un producto en el carrito del usuario autenticado.
        Requiere 'product_id' y 'quantity' en el cuerpo de la solicitud.
        """
        cart = self.get_queryset().first() # Obtenemos el carrito del usuario autenticado
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 0)) # Cantidad esperada
        print('aqui', quantity)
        if quantity <= 0:
            return Response({"error": "Quantity must be positive."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_400_BAD_REQUEST)

        # Validar stock antes de añadir/actualizar en el carrito
        # Si el item ya existe, sumamos la cantidad existente a la nueva cantidad para la validación
        existing_item = cart.items.filter(id=product_id).first()
        total_quantity_requested = quantity + (existing_item.quantity if existing_item else 0)
        if product.stock < total_quantity_requested:
            return Response({"error": f"Insufficient stock.  Only {product.stock} available for {product.name} (already in cart: {existing_item.quantity if existing_item else 0})."}, status=status.HTTP_400_BAD_REQUEST)

        # Usamos get_or_create para manejar si el item ya está en el carrito
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={'quantity': quantity})
        if not created:
            cart_item.quantity = total_quantity_requested # Actualiza la cantidad total
            cart_item.save()

        cart.refresh_from_db() # Para asegurar que cualquier cálculo en el modelo Cart se actualice
        serializer = self.get_serializer(cart)
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
        # return Response(status=status.HTTP_204_NO_CONTENT)
        cart.refresh_from_db() # Para asegurar que cualquier cálculo en el modelo Cart se actualice
        serializer = self.get_serializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def create_quote(self, request):

        cart = self.get_queryset().first()
        if not cart or not cart.items.exists():
            return Response({"error": "El carrito está vacío."}, status=status.HTTP_400_BAD_REQUEST)

        user_id_from_payload = request.data.get('user_id')
        customer_data = request.data.get('customer', {})
        
        quote_user = None # El usuario que quedará asociado a la Quote

        # --- LÓGICA DE ASIGNACIÓN DE USUARIO REVISADA ---
        # 1. Si se proporciona un ID de usuario en el payload (venta de POS para un cliente existente)
        if user_id_from_payload:
            # Solo un staff puede asignar una venta a otro usuario
            if not request.user.is_staff:
                return Response({"error": "No tienes permiso para crear una cotización para otro usuario."}, status=status.HTTP_403_FORBIDDEN)
            
            try:
                # Obtener el cliente al que se le asignará la cotización
                quote_user = User.objects.get(pk=user_id_from_payload)
            except User.DoesNotExist:
                return Response({"error": f"El cliente con ID {user_id_from_payload} no fue encontrado."}, status=status.HTTP_400_BAD_REQUEST)
            except (ValueError, TypeError):
                return Response({"error": "El user_id proporcionado no es válido."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Si no se proporciona un ID de usuario, y el usuario logueado es un cliente normal
        elif request.user.is_authenticated and not request.user.is_staff:
            quote_user = request.user

        # 3. Si el usuario logueado es un staff y NO proporciona un user_id,
        # O si la solicitud es de un usuario no autenticado (si lo permitieras),
        # entonces quote_user permanece None, y se crea como una venta de invitado.
        
        # --- FIN LÓGICA DE ASIGNACIÓN ---

        # Rellenar datos del cliente si no se proporcionaron y se asoció un usuario
        customer_name = customer_data.get('name', '')
        customer_email = customer_data.get('email', '')
        customer_document = customer_data.get('document', '')
        customer_phone = customer_data.get('phone', '')

        if quote_user and not customer_name and not customer_email:
            customer_name = quote_user.get_full_name() or quote_user.username
            customer_email = quote_user.email
            if hasattr(quote_user, 'profile'):
                customer_document = quote_user.profile.document or ''
                customer_phone = quote_user.profile.phone or ''

        try:
            with transaction.atomic():
                quote = Quote.objects.create(
                    user=quote_user, # Asignar el usuario encontrado/logueado, o None
                    cart=cart,
                    status='pending',
                    total=Decimal('0.00'),
                    customer_name=customer_name,
                    customer_email=customer_email,
                    customer_document=customer_document,
                    customer_phone=customer_phone,
                )
                
                # ... (código para crear QuoteItems y calcular el total) ...
                # Esta parte no necesita cambios
                quote_total = Decimal('0.00')
                cart_items = cart.items.all()
                quote_items_to_create = []
                for item in cart_items:
                    price_at_quote = item.product.final_sale_price
                    quote_item_instance = QuoteItem(quote=quote, product=item.product, quantity=item.quantity, price_at_quote=price_at_quote)
                    quote_items_to_create.append(quote_item_instance)
                    quote_total += quote_item_instance.subtotal
                
                QuoteItem.objects.bulk_create(quote_items_to_create)
                quote.total = quote_total
                quote.save()
                cart_items.delete()
                

        except Exception as e:
            return Response({"error": f"Ocurrió un error inesperado al crear la cotización: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        send_quote_pdf_email.delay(quote.id)
        serializer = QuoteSerializer(quote, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class QuoteViewSet(viewsets.ModelViewSet):
    serializer_class = QuoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    # --- AÑADIR CONFIGURACIÓN DE FILTRADO Y BÚSQUEDA ---
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    
    # Campos por los que el admin podrá buscar texto libre
    search_fields = [
        'id', # Buscar por ID de cotización
        'user__username', # Buscar por username del cliente
        'user__email', # Buscar por email del cliente
        'user__profile__document', # Buscar por documento del cliente (si tienes perfil)
    ]
    
    # Campos por los que el admin podrá filtrar con valores exactos (ej. ?status=pending)
    filterset_fields = ['status']
    
    # Campos por los que se podrá ordenar
    ordering_fields = ['id', 'created_at', 'total', 'user__email']
    ordering = ['-created_at'] # Orden por defecto

    # --- ANOTACIONES DE SCHEMA MEJORADAS A NIVEL DE CLASE ---
    # Esto se aplicará a los métodos de detalle (retrieve, update, etc.)
    # y es menos repetitivo.
    @extend_schema(
        parameters=[
            OpenApiParameter(name='id', description='Un valor entero único que identifica esta cotización.', required=True, type=OpenApiTypes.INT, location=OpenApiParameter.PATH)
        ]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    # Puedes omitir las redefiniciones de update, partial_update, destroy
    # si no tienen lógica personalizada. @extend_schema en la clase padre
    # o en retrieve a menudo es suficiente para que spectacular entienda el parámetro.
    # Si aún así necesitas ser explícito, mantenlos, pero con la descripción correcta.

    def get_queryset(self):
        """
        Permite a los administradores ver todas las cotizaciones.
        Permite a los usuarios normales ver solo sus propias cotizaciones.
        El filtrado, búsqueda y ordenamiento se aplicarán sobre el queryset base devuelto.
        """

        # Usar select_related y prefetch_related para optimizar consultas
        # al obtener datos relacionados (usuario, items, producto del item, etc.)
        queryset = Quote.objects.all().select_related(
            'user', 'user__profile'
        ).prefetch_related(
            'items', 'items__product'
        )

        # Si el usuario NO es staff, filtramos para que solo vea lo suyo.
        # Si ES staff, no aplicamos este filtro, por lo que verá todo.
        # Los filtros de la URL (status, search) serán aplicados por DRF
        # después de que este método devuelva el queryset.
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
            
        return queryset

    @action(detail=True, methods=['post'])
    def finalize_sale(self, request, pk=None):
        """
        Finaliza la venta de una cotización (cambia el estado a 'paid').
        Solo accesible para administradores.
        La lógica de descuento de stock se encuentra aquí.
        """
        if not self.request.user.is_staff:
            return Response({"error": "No autorizado para realizar esta acción."}, status=status.HTTP_403_FORBIDDEN)

        quote = self.get_object()
        if quote.status != 'pending':
            return Response({"error": f"La cotización ya no está pendiente. Estado actual: {quote.status}."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # --- LÓGICA DE DESCUENTO DE STOCK ---
                # Esta lógica ahora vive aquí, no en create_quote.
                for item in quote.items.all():
                    # Bloquear la fila del producto para evitar race conditions
                    product = Product.objects.select_for_update().get(pk=item.product.pk)
                                        
                    if product.stock < item.quantity:
                        # Si no hay suficiente stock, revertir toda la transacción
                        raise ValueError(f"Stock insuficiente para finalizar la venta del producto '{product.name}'. Disponible: {product.stock}, Solicitado: {item.quantity}")
                    
                    # Si hay stock, descontarlo
                    product.stock -= item.quantity
                    product.save()
                
                # Cambiar el estado de la cotización
                quote.status = 'paid'
                quote.save()
                
                # Aquí podrías añadir lógica adicional como enviar un correo de confirmación de pago.

        except ValueError as e: # Captura el error de stock que lanzamos
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e: # Captura cualquier otro error inesperado
            # Considera loguear el error real
            # logger.error(f"Error finalizando la venta para quote {quote.id}: {e}")
            return Response({"error": "Ocurrió un error inesperado al procesar la venta."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        send_invoice_pdf_email.delay(quote.id)
        serializer = self.get_serializer(quote)
        return Response({
            "message": f"Venta para la cotización #{quote.pk} finalizada exitosamente. Estado cambiado a 'pagado'.", 
            "quote": serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def cancel_quote(self, request, pk=None):
        """
        Cancela una cotización. Si el stock fue descontado (ej. de un estado 'paid'), lo restaura.
        Si está 'pending', solo cambia el estado.
        """
        quote = self.get_object()

        if not self.request.user.is_staff and quote.user != self.request.user:
            return Response({"error": "No autorizado para cancelar esta cotización."}, status=status.HTTP_403_FORBIDDEN)

        # Se puede cancelar si está 'pending' o 'paid' (para un reembolso)
        if quote.status not in ['pending', 'paid']:
            return Response({"error": f"La cotización no se puede cancelar. Estado actual: {quote.status}"}, status=status.HTTP_400_BAD_REQUEST)

        # Guardar el estado anterior para saber si debemos restaurar stock
        previous_status = quote.status

        with transaction.atomic():
            quote.status = 'cancelled'
            quote.save()

            # Restaurar stock SOLO si venía de un estado donde el stock ya había sido descontado
            # (En nuestro nuevo flujo, esto es solo si el estado era 'paid')
            if previous_status == 'paid':
                for item in quote.items.all():
                    # select_for_update también es bueno aquí
                    product = Product.objects.select_for_update().get(pk=item.product.pk)
                    product.stock += item.quantity
                    product.save()

        serializer = QuoteSerializer(quote)
        return Response({
            "message": f"Cotización #{quote.pk} cancelada exitosamente." + (" Stock restaurado." if previous_status == 'paid' else ""), 
            "quote": serializer.data
        }, status=status.HTTP_200_OK)

    # --- NUEVA ACCIÓN SUGERIDA ---
    @action(detail=True, methods=['post'], url_path='mark-as-shipped')
    def mark_as_shipped(self, request, pk=None):
        """
        Marca una cotización pagada como enviada. Solo para administradores.
        """
        if not self.request.user.is_staff:
            return Response({"error": "No autorizado para realizar esta acción."}, status=status.HTTP_403_FORBIDDEN)

        quote = self.get_object()
        if quote.status != 'paid':
            return Response({"error": f"Solo se pueden marcar como enviadas las cotizaciones pagadas. Estado actual: {quote.status}"}, status=status.HTTP_400_BAD_REQUEST)

        quote.status = 'shipped'
        quote.save()
        
        # Aquí podrías añadir lógica para enviar un correo de notificación de envío al cliente.

        serializer = self.get_serializer(quote)
        
        return Response({
            "message": f"Cotización #{quote.pk} marcada como enviada.",
            "quote": serializer.data
        }, status=status.HTTP_200_OK)