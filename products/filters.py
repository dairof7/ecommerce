# products/filters.py
import django_filters
from .models import Product, Tag

class ProductFilter(django_filters.FilterSet):
    # Filtro por nombre de producto (búsqueda 'icontains')
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    # Filtro por categoría (usa el ID)
    category = django_filters.NumberFilter(field_name='category__id') # O ModelChoiceFilter

    # Filtro por subcategoría (usa el ID)
    subcategory = django_filters.NumberFilter(field_name='subcategory__id') # O ModelChoiceFilter

    # Filtro por Tags (acepta múltiples IDs de tags, busca productos que tengan TODOS los tags especificados)
    # Este es el comportamiento por defecto de ManyToManyField con filterset_fields
    # tags = django_filters.ModelMultipleChoiceFilter(
    #     queryset=Tag.objects.all(),
    #     field_name='tags',
    #     to_field_name='id', # El campo del modelo Tag a usar para el valor del filtro
    #     conjoined=True, # True para AND (todos los tags), False para OR (cualquier tag) - por defecto es False si no lo pones en filterset_fields
    # )

    # Filtro por Tags usando NOMBRES de tags (más amigable para URLs)
    # Aceptará ?tags_name=FullHD&tags_name=Portatil
    tags_name = django_filters.ModelMultipleChoiceFilter(
        field_name='tags__name', # Busca en el campo 'name' del modelo Tag relacionado
        to_field_name='name',    # El valor que se envía en la URL es el nombre del tag
        queryset=Tag.objects.all(),
        conjoined=True, # True = AND (el producto debe tener todos los tags_name especificados)
                       # False = OR (el producto debe tener al menos uno de los tags_name especificados)
        label="Filtrar por nombres de tags (separados por comas si se configura el widget o se usa un conversor)"
    )
    # Si quieres que acepte ?tags_name=FullHD,Portatil, necesitarías un CharFilter y parsearlo

    class Meta:
        model = Product
        # Los campos definidos arriba tienen precedencia sobre estos.
        # Estos son para filtros de igualdad exactos si no se definen explícitamente arriba.
        fields = ['category', 'subcategory'] # 'tags' se maneja arriba con más control