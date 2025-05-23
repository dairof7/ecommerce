from django.db import models

class Banner(models.Model):
    PLACEMENT_CHOICES = [
        ('home_main', 'Home - Carrusel Principal'),
        ('home_secondary', 'Home - Sección Secundaria'),
        ('product_list_top', 'Listado de Productos - Superior'),
        ('product_list_sidebar', 'Listado de Productos - Barra Lateral'),
        ('product_detail_related', 'Detalle de Producto - Relacionados'),
        ('general_sitewide_top', 'General - Encabezado Sitio'),
    ]

    name = models.CharField("Nombre del Banner (interno)", max_length=100)
    image = models.ImageField("Imagen del Banner", upload_to='banners/')
    alt_text = models.CharField("Texto Alternativo (SEO y Accesibilidad)", max_length=255, blank=True)
    link_url = models.URLField("URL de Destino (opcional)", blank=True, null=True)
    placement = models.CharField(
        "Ubicación del Banner",
        max_length=50,
        choices=PLACEMENT_CHOICES,
        db_index=True
    )
    order = models.PositiveIntegerField("Orden de Visualización", default=0, help_text="Menor número se muestra primero en la misma ubicación.")
    is_active = models.BooleanField("Activo", default=True, db_index=True)
    start_date = models.DateTimeField("Fecha de Inicio (opcional)", blank=True, null=True)
    end_date = models.DateTimeField("Fecha de Fin (opcional)", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Banner"
        verbose_name_plural = "Banners"
        ordering = ['placement', 'order', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_placement_display()})"

    def is_currently_active(self):
        if not self.is_active:
            return False
        from django.utils import timezone # Importar aquí para evitar importación circular si timezone usa settings al inicio
        now = timezone.now()
        if self.start_date and self.start_date > now:
            return False
        if self.end_date and self.end_date < now:
            return False
        return True