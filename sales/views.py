from rest_framework import viewsets, permissions
from .models import Discount
from .serializers import DiscountSerializer

class DiscountViewSet(viewsets.ModelViewSet):
    queryset = Discount.objects.all()
    serializer_class = DiscountSerializer
    permission_classes = [permissions.IsAdminUser]