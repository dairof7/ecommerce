from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Cart, CartItem, Quote, Product
from .serializers import CartSerializer, CartItemSerializer, QuoteSerializer
from rest_framework.permissions import IsAuthenticated

class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]
    # permission_classes = [permissions.AllowAny]
    # permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        cart, created = Cart.objects.get_or_create(user=user)
        return Cart.objects.filter(user=user)

    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        # cart = self.get_object()
        cart = self.get_queryset().first()
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_400_BAD_REQUEST)

        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={'quantity': quantity})
        if product.stock < (quantity + cart_item.quantity):
            return Response({"error": f"Insufficient stock.  Only {product.stock} available."}, status=status.HTTP_400_BAD_REQUEST)

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        serializer = CartItemSerializer(cart_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='remove_item/(?P<item_id>\d+)')
    def remove_item(self, request, pk=None, item_id=None):
        cart = self.get_object()

        try:
            cart_item = CartItem.objects.get(cart=cart, pk=item_id)
        except CartItem.DoesNotExist:
            return Response({"error": "Item not found in cart."}, status=status.HTTP_404_NOT_FOUND)

        cart_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def create_quote(self, request, pk=None):
        cart = self.get_object()

        # Validar que el stock sea suficiente para todos los items
        for item in cart.items.all():
            if item.product.stock < item.quantity:
                return Response({"error": f"Insufficient stock for {item.product.name}"}, status=status.HTTP_400_BAD_REQUEST)

        # Calcular el total de la cotización
        total = 0
        for item in cart.items.all():
            total += item.product.sale_price * item.quantity

        quote = Quote.objects.create(cart=cart, total=total)
        serializer = QuoteSerializer(quote)

        #Descontar stock (puedes mover esto a una tarea asíncrona si lo prefieres)
        for item in cart.items.all():
            product = item.product
            product.stock -= item.quantity
            product.save() # Guarda la modificación del stock

        return Response(serializer.data, status=status.HTTP_201_CREATED)

class QuoteViewSet(viewsets.ModelViewSet):
    serializer_class = QuoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Quote.objects.all()
        else:
            return Quote.objects.filter(cart__user=self.request.user)

    @action(detail=True, methods=['post'])
    def finalize_sale(self, request, pk=None):
        if not self.request.user.is_staff:
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        quote = self.get_object()
        if quote.status != 'pending':
            return Response({"error": "Quote is not pending."}, status=status.HTTP_400_BAD_REQUEST)

        quote.status = 'paid'
        quote.save()

        return Response({"message": "Sale finalized successfully."}, status=status.HTTP_200_OK)