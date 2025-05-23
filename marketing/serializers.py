# site_settings/serializers.py
from rest_framework import serializers
from .models import Banner

class BannerSerializer(serializers.ModelSerializer):
    image_url = serializers.ImageField(source='image', read_only=True) # Para servir la URL de la imagen

    class Meta:
        model = Banner
        fields = ['id', 'name', 'image_url', 'alt_text', 'link_url', 'placement', 'order', 'is_active']
        read_only_fields = ['name', 'is_active', 'order']
        # 'name', 'is_active', 'order' podrían ser read_only si solo se gestionan desde el admin
        # y la API solo los consume.
        # Si la API también los crea/modifica, quita read_only para esos.