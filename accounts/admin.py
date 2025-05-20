from django.contrib import admin
from .models import UserProfile



@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user','user__email', 'address', 'document', 'phone')  # Campos a mostrar en la lista
    search_fields = ('user__username', 'document', 'phone', 'user__email')  # Campos para buscar
    list_filter = ('user__is_active', )  # Filtros en la barra lateral
    readonly_fields = ('user',) # evita que se modifique el usuario

    fieldsets = (
        (None, {
            'fields': ('user',)
        }),
        ('Información Personal', {
            'fields': ('address', 'document', 'phone')
        }),
    )