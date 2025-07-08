import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from faker import Faker  # pip install Faker
from products.models import Category, Subcategory, Product, Tag, ProductImage
from django.contrib.auth import get_user_model
from django.db import IntegrityError
# Opcional: si quieres usar tus factorías de test (ajustándolas si es necesario)
# from products.tests.factories import CategoryFactory, SubcategoryFactory, ProductFactory, TagFactory
# from accounts.tests.factories import UserFactory
from accounts.models import UserProfile
User = get_user_model()
fake = Faker(['es_ES', 'en_US'])  # Para datos en español e inglés


class Command(BaseCommand):
    help = 'Populates the database with initial data for categories, subcategories, products, etc.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting data population...'))

        # Limpiar datos existentes (¡CUIDADO! Solo para desarrollo)
        # Descomenta bajo tu propio riesgo y solo en entornos de desarrollo.
        # Tag.objects.all().delete()
        # ProductImage.objects.all().delete()
        # Product.objects.all().delete()
        # Subcategory.objects.all().delete()
        # Category.objects.all().delete()
        # User.objects.filter(is_superuser=False).delete() # No borrar superusuarios
        # self.stdout.write(self.style.WARNING('Existing data cleared.'))

        # --- Crear Categorías ---
        self.stdout.write('Creating categories...')
        categories_data = ["Electrónica", "Ropa",
                           "Hogar", "Libros", "Deportes"]
        categories = {}  # Para guardar las instancias creadas
        for cat_name in categories_data:
            category, created = Category.objects.get_or_create(name=cat_name)
            categories[cat_name] = category
            if created:
                self.stdout.write(f'  Created category: {category.name}')

        # --- Crear Subcategorías ---
        self.stdout.write('Creating subcategories...')
        subcategories_data = {
            "Electrónica": ["Teléfonos Móviles", "Portátiles", "Audio y Video", "Accesorios"],
            "Ropa": ["Camisetas", "Pantalones", "Zapatos", "Abrigos"],
            "Hogar": ["Muebles", "Decoración", "Cocina", "Jardín"],
            "Libros": ["Ficción", "No Ficción", "Ciencia Ficción", "Biografías"],
            "Deportes": ["Fútbol", "Baloncesto", "Running", "Ciclismo"],
        }
        subcategories = {}
        for cat_name, sub_names in subcategories_data.items():
            parent_category = categories.get(cat_name)
            if parent_category:
                for sub_name in sub_names:
                    subcategory, created = Subcategory.objects.get_or_create(
                        name=sub_name, category=parent_category
                    )
                    subcategories[sub_name] = subcategory  # Guardar referencia
                    if created:
                        self.stdout.write(
                            f'  Created subcategory: {subcategory.name} (under {parent_category.name})')

        # --- Crear Tags ---
        self.stdout.write('Creating tags...')
        tags_data = ["Oferta", "Nuevo", "Popular",
                    "Edición Limitada", "Envío Gratis", "Importado", "Nacional"]
        created_tags = []
        for tag_name in tags_data:
            tag, created = Tag.objects.get_or_create(name=tag_name)
            created_tags.append(tag)
            if created:
                self.stdout.write(f'  Created tag: {tag.name}')

        # --- Crear Productos ---
        self.stdout.write('Creating products...')
        num_products_to_create = options.get(
            'num_products', 20)  # Puedes pasar un argumento

        all_categories = list(Category.objects.all())
        all_subcategories = list(Subcategory.objects.all())

        for i in range(num_products_to_create):
            category = random.choice(all_categories)
            # Elegir una subcategoría que pertenezca a la categoría seleccionada
            possible_subcats = [
                s for s in all_subcategories if s.category == category]
            # Si la categoría no tiene subcategorías (debería tenerlas)
            if not possible_subcats:
                self.stdout.write(self.style.WARNING(
                    f'Category {category.name} has no subcategories. Skipping product creation for this iteration.'))
                continue
            subcategory = random.choice(possible_subcats)

            name = f"{fake.bs().capitalize()} {subcategory.name} Pro v{random.randint(1, 10)}"
            description = fake.paragraph(nb_sentences=5)
            purchase_price = Decimal(random.uniform(
                10000, 500000)).quantize(Decimal("0.01"))
            sale_price = purchase_price * \
                Decimal(random.uniform(1.2, 2.5)).quantize(Decimal("0.01"))
            stock = random.randint(0, 100)
            discount = Decimal(random.choice(
                [0, 0, 0, 5, 10, 15, 0, 20])).quantize(Decimal("0.01"))

            product, created = Product.objects.get_or_create(
                name=name,
                defaults={  # Solo se usan si el objeto no existe
                    'category': category,
                    'subcategory': subcategory,
                    'description': description,
                    'purchase_price': purchase_price,
                    'sale_price': sale_price,
                    'stock': stock,  # El stock inicial
                    'discount': discount
                }
            )

            if created:
                # Asignar tags aleatorios
                num_tags_for_product = random.randint(
                    0, min(3, len(created_tags)))
                tags_for_product = random.sample(
                    created_tags, num_tags_for_product)
                product.tags.set(tags_for_product)

                # Opcional: Crear imágenes de producto (requiere manejo de archivos)
                for _ in range(random.randint(1, 3)):
                    # Aquí necesitarías una imagen real o un placeholder
                    ProductImage.objects.create(product=product, image='products/3.png', alt_text=f"Imagen de {product.name}")
                    # pass
                self.stdout.write(f'  Created product: {product.name}')
            else:
                self.stdout.write(self.style.WARNING(
                    f'  Product already exists: {product.name}'))

        # --- Crear Usuarios (opcional) ---
        self.stdout.write('Creating sample users...')

            
            
            
            
        self.stdout.write('Creating sample users...')
        # num_users_to_create = 5
        # for i in range(num_users_to_create):
        #     # Generar datos únicos para cada intento
        #     # Usar un sufijo para asegurar unicidad si Faker genera duplicados rápidamente
        #     base_username = fake.user_name().lower().replace(' ', '_')
        #     username = f"{base_username}_{i}"
        #     email = fake.email() # Faker debería generar emails únicos la mayoría de las veces
        #     # Si usas email como USERNAME_FIELD y es unique=True, asegúrate de que email sea único aquí.
        #     # email = f"user{i}_{fake.domain_name()}" # Una forma de asegurar unicidad del email

        #     try:
        #         user_instance = User.objects.create_user(
        #             username=username,
        #             email=email,
        #             password='password123'
        #         )
        #         # Opcional: Crear UserProfile si no se crea automáticamente por señales
        #         # y si tu AUTH_USER_MODEL no lo maneja.
        #         # if hasattr(user_instance, 'profile'): # Si tienes una relación 'profile'
        #         #     if not UserProfile.objects.filter(user=user_instance).exists():
        #         #         UserProfile.objects.create(user=user_instance, address=fake.address())
        #         UserProfile.objects.create(
        #             user=user_instance,
        #             address=fake.address(),
        #             document=fake.ssn(), # O un generador más apropiado
        #             phone=fake.phone_number()
        #         )
        #         self.stdout.write(self.style.SUCCESS(f'  Successfully created user: {user_instance.username} (Email: {user_instance.email})'))
        #     except IntegrityError as e:
        #         self.stdout.write(self.style.ERROR(f'  Error creating user (username: {username}, email: {email}): {e}. Skipping.'))
        #     except Exception as e:
        #         self.stdout.write(self.style.ERROR(f'  An unexpected error occurred creating user (username: {username}, email: {email}): {e}. Skipping.'))
        
        # self.stdout.write(self.style.SUCCESS(f'{User.objects.filter(is_superuser=False).count()} sample users in database.'))
            
            
            
            
        self.stdout.write(self.style.SUCCESS('Sample users created.'))

        self.stdout.write(self.style.SUCCESS(
            'Data population finished successfully!'))

    def add_arguments(self, parser):
        parser.add_argument(
            '--num_products',
            type=int,
            default=30,  # Valor por defecto si no se especifica
            help='Number of products to create'
        )
