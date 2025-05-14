from rest_framework import viewsets, permissions
from .models import StockEntry
from .serializers import StockEntrySerializer

class StockEntryViewSet(viewsets.ModelViewSet):
    queryset = StockEntry.objects.all()
    serializer_class = StockEntrySerializer
    permission_classes = [permissions.IsAdminUser]