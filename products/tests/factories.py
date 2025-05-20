# products/tests/factories.py
from decimal import Decimal
import factory
from factory.django import DjangoModelFactory
from faker import Faker
from products.models import Product, Category, Subcategory, Tag
# Importa las factorías que vas a usar como SubFactory
# from .factories import CategoryFactory, SubcategoryFactory, TagFactory # Esto sería una importación circular
# Es mejor definirlas antes o importarlas de otro módulo si estuvieran separadas

fake = Faker()

class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category
    name = factory.Faker('word')

class SubcategoryFactory(DjangoModelFactory):
    class Meta:
        model = Subcategory
    name = factory.Faker('word')
    category = factory.SubFactory(CategoryFactory) # Correcto: usa la factoría definida arriba

class TagFactory(DjangoModelFactory):
    class Meta:
        model = Tag
    name = factory.Faker('slug')


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product
        skip_postgeneration_save = True

    name = factory.LazyAttribute(lambda obj: fake.company() + " Product")
    description = factory.Faker('paragraph', nb_sentences=3)
    category = factory.SubFactory(CategoryFactory)

    # --- POSIBLE PUNTO DEL PROBLEMA ---
    # Si 'subcategory' no se define explícitamente aquí,
    # o si el hook 'ensure_subcategory_consistency' no la asigna correctamente ANTES del guardado inicial,
    # podría ser None.

    # Opción 1: Asignar directamente una SubFactory (pero debe ser consistente con category)
    # Esta es la forma más directa si puedes asegurar la consistencia aquí.
    # La clave es que la SubcategoryFactory necesita saber sobre la 'category' del producto.
    subcategory = factory.SubFactory(
        SubcategoryFactory,
        category=factory.SelfAttribute('..category') # '..' accede al contenedor (ProductFactory)
                                                     # y '.category' a su atributo category.
    )

    # Opción 2: Dejar que el hook post_generation la cree (menos ideal si es NOT NULL)
    # Si 'subcategory' fuera opcional (null=True en el modelo), podrías hacer:
    # subcategory = None
    # Y luego en el @factory.post_generation la crearías. Pero como es NOT NULL,
    # debe tener un valor ANTES del primer .save() que hace DjangoModelFactory.

    purchase_price = factory.Faker('pydecimal', left_digits=3, right_digits=2, positive=True)
    sale_price = factory.LazyAttribute(lambda obj: obj.purchase_price * fake.pydecimal(left_digits=1, right_digits=2, positive=True, min_value=Decimal('1.1'), max_value=Decimal('2.0')))
    stock = factory.Faker('random_int', min=0, max=100)
    discount = factory.Faker('pydecimal', left_digits=2, right_digits=2, min_value=Decimal('0.00'), max_value=Decimal('50.00'))

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for tag in extracted:
                self.tags.add(tag)
        else:
            num_tags = fake.random_int(min=0, max=3)
            for _ in range(num_tags):
                self.tags.add(TagFactory())