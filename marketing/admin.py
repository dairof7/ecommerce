# site_settings/admin.py
from django.contrib import admin
from .models import Banner

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('name', 'placement', 'order', 'is_active', 'start_date', 'end_date', 'link_url_display')
    list_filter = ('placement', 'is_active', 'start_date', 'end_date')
    search_fields = ('name', 'alt_text', 'link_url')
    list_editable = ('order', 'is_active')
    ordering = ('placement', 'order')

    # Para mostrar un fragmento de la URL o un enlace si es muy larga
    def link_url_display(self, obj):
        if obj.link_url:
            return f'<a href="{obj.link_url}" target="_blank">{obj.link_url[:50]}...</a>' if len(obj.link_url) > 50 else f'<a href="{obj.link_url}" target="_blank">{obj.link_url}</a>'
        return "-"
    link_url_display.allow_tags = True # Necesario para Django < 4.0 si usas HTML
    link_url_display.short_description = "URL de Destino"