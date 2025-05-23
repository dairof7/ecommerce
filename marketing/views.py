# site_settings/views.py
from rest_framework import viewsets, permissions, mixins
from django.utils import timezone
from django.db.models import Q
from .models import Banner
from .serializers import BannerSerializer

class BannerViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Endpoint para listar banners activos.
    Permite filtrar por 'placement'.
    Ejemplo: /api/site-settings/banners/?placement=home_main
    """
    serializer_class = BannerSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        now = timezone.now()
        queryset = Banner.objects.filter(
            is_active=True
        ).filter(
            Q(start_date__lte=now) | Q(start_date__isnull=True)
        ).filter(
            Q(end_date__gte=now) | Q(end_date__isnull=True)
        ).order_by('placement', 'order') # Ordenar para consistencia

        placement_filter = self.request.query_params.get('placement', None)
        if placement_filter:
            queryset = queryset.filter(placement=placement_filter)
        
        return queryset