import pytest
from django.urls import reverse # Para generar URLs de API
from django.core.management import call_command # Para llamar a loaddata
from rest_framework import status # Para códigos de estado HTTP
from rest_framework.test import APIClient # Cliente de prueba de DRF
from products.models import Product, Category, Subcategory, Tag # Tus modelos
from .factories import ProductFactory, CategoryFactory, SubcategoryFactory, TagFactory # Tus factorías
from accounts.tests.factories import UserFactory # Factoría de usuarios de otra app

# pytest.mark.django_db es crucial para que los tests tengan acceso a la base de datos
# y se ejecuten dentro de una transacción que se revierte después de cada test.
pytestmark = pytest.mark.django_db


# --- Fixture para cargar datos iniciales de categorías y subcategorías ---
@pytest.fixture(scope='session', autouse=True) # Se ejecuta una vez por sesión de test, automáticamente
def load_initial_categories_subcategories(django_db_setup, django_db_blocker):
    """
    Carga las fixtures de categorías y subcategorías desde el archivo JSON
    una vez por sesión de test.
    """
    with django_db_blocker.unblock(): # Permite escrituras a la BD durante la carga de fixtures
        print("\nCargando fixtures: initial_categories_subcategories.json...")
        call_command('loaddata', 'initial_categories_subcategories.json')
        print("Fixtures cargadas.")


# --- Fixtures para Clientes de API ---
@pytest.fixture
def api_client():
    """Fixture para un cliente de API no autenticado."""
    return APIClient()

@pytest.fixture
def authenticated_user_client():
    """Fixture para un cliente de API autenticado como usuario regular."""
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    return client

@pytest.fixture
def admin_user_client():
    """Fixture para un cliente de API autenticado como admin."""
    admin_user = UserFactory(is_staff=True, is_superuser=True)
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


# --- Tests para el endpoint de listar productos ---
# Este test ahora puede asumir que las categorías/subcategorías de la fixture existen
# si ProductFactory las usa (o si creas productos directamente con ellas).
def test_list_products_unauthenticated(api_client):
    # Crear productos. ProductFactory usará sus propias CategoryFactory/SubcategoryFactory
    # a menos que explícitamente le pases instancias de las cargadas por fixture.
    # Para este test, podemos seguir creando productos con factorías.
    ProductFactory.create_batch(3)

    url = reverse('product-list')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data['results']) >= 3


# --- Tests para el endpoint de crear producto usando datos de fixture ---
def test_create_product_by_admin_with_fixture_categories(admin_user_client):
    # Obtener categorías y subcategorías cargadas desde la fixture
    # Asumimos que "Electrónica" tiene pk=1 y "Teléfonos Móviles" tiene pk=1 y pertenece a Electrónica.
    # Es mejor obtenerlos por un atributo más estable que el PK si el PK pudiera cambiar,
    # pero para fixtures controladas, el PK está bien.
    try:
        category_electronica = Category.objects.get(name="Electrónica") # O por pk=1
        subcategory_telefonos = Subcategory.objects.get(name="Teléfonos Móviles", category=category_electronica)
    except (Category.DoesNotExist, Subcategory.DoesNotExist) as e:
        pytest.fail(f"Error obteniendo datos de fixture: {e}. Asegúrate que la fixture 'initial_categories_subcategories.json' se cargó.")
    tag1 = TagFactory(name="Nuevo")
    tag2 = TagFactory(name="Oferta")

    product_data = {
        'name': 'Nuevo Teléfono de Fixture con Tags',
        'description': 'Un teléfono creado con categorías de fixture y tags.',
        'category_id': category_electronica.id, # Usar los campos _id para la entrada
        'subcategory_id': subcategory_telefonos.id, # Usar los campos _id para la entrada
        'purchase_price': '300.00',
        'sale_price': '450.00',
        # 'stock': 15, # Comentado porque stock es read_only en el serializador
        'discount': '0.00',
        'tag_ids': [tag1.id, tag2.id] # Usar el nuevo campo 'tag_ids'
    }
    
    url = reverse('product-list')
    response = admin_user_client.post(url, product_data, format='json')

    print("Response data on create (fixture cat, with tags):", response.data)
    assert response.status_code == status.HTTP_201_CREATED
    
    created_product = Product.objects.get(name=product_data['name'])
    assert created_product.category == category_electronica
    assert created_product.subcategory == subcategory_telefonos
    
    # Verificar los tags
    assert created_product.tags.count() == 2
    assert tag1 in created_product.tags.all()
    assert tag2 in created_product.tags.all()

    # Verificar que la respuesta del API también muestra los tags (objetos completos)
    assert 'tags' in response.data
    assert len(response.data['tags']) == 2
    # Puedes verificar que los nombres de los tags en la respuesta coincidan
    response_tag_names = {t['name'] for t in response.data['tags']}
    assert tag1.name in response_tag_names
    assert tag2.name in response_tag_names


def test_create_product_by_regular_user_forbidden(authenticated_user_client):
    # Puedes usar categorías de fixture aquí también si quieres ser consistente
    category = Category.objects.first() # Toma la primera categoría de la fixture
    if not category:
        category = CategoryFactory() # Fallback si la fixture no cargó nada
    
    # Asegurar que la subcategoría sea hija de la categoría
    subcategory = Subcategory.objects.filter(category=category).first()
    if not subcategory:
        subcategory = SubcategoryFactory(category=category)

    product_data = {
        'name': 'Forbidden Product',
        'category_id': category.id,
        'subcategory_id': subcategory.id,
        'purchase_price': '10.00', 'sale_price': '20.00'
    }
    url = reverse('product-list')
    response = authenticated_user_client.post(url, product_data, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_product_invalid_data(admin_user_client):
    invalid_data = {
        'description': 'Product without name',
        'purchase_price': '10.00', 'sale_price': '20.00'
    }
    url = reverse('product-list')
    response = admin_user_client.post(url, invalid_data, format='json')
    print('response: --', response.data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'name' in response.data
    assert 'category_id' in response.data # O el campo que falte
    assert 'subcategory_id' in response.data # O el campo que falte


# --- Tests para el endpoint de detalle de producto ---
def test_retrieve_product_detail(api_client):
    # Aquí ProductFactory creará un producto con sus propias cat/subcat (a menos que lo modifiques)
    # o puedes crear un producto usando las cats/subcats de la fixture.
    cat_fixture = Category.objects.filter(name="Ropa").first() or CategoryFactory()
    subcat_fixture = Subcategory.objects.filter(category=cat_fixture, name="Camisetas").first() or SubcategoryFactory(category=cat_fixture)
    
    product = ProductFactory(category=cat_fixture, subcategory=subcat_fixture)
    
    url = reverse('product-detail', kwargs={'pk': product.pk})
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data['name'] == product.name
    assert response.data['category']['id'] == cat_fixture.id # Verifica el ID de la categoría del producto
    assert response.data['subcategory']['id'] == subcat_fixture.id # Verifica el ID de la subcategoría


def test_update_product_by_admin(admin_user_client):
    # Crear un producto inicial, puede ser con factorías que generan sus propias cat/subcat
    product_to_update = ProductFactory(name="Old Name")

    # Nuevos datos para actualizar, usando categorías/subcategorías de la fixture
    new_category = Category.objects.get(name="Hogar") # Asume que "Hogar" existe en la fixture
    new_subcategory = Subcategory.objects.get(name="Muebles de Sala", category=new_category)

    update_data = {
        'name': 'Updated Product Name Using Fixture Cat',
        'sale_price': '120.50',
        'purchase_price': '80.00',
        'category_id': new_category.id,
        'subcategory_id': new_subcategory.id
    }
    url = reverse('product-detail', kwargs={'pk': product_to_update.pk})
    response = admin_user_client.put(url, update_data, format='json')
    print("Response data on update (fixture cat):", response.data)
    assert response.status_code == status.HTTP_200_OK
    product_to_update.refresh_from_db()
    assert product_to_update.name == update_data['name']
    assert product_to_update.category == new_category
    assert product_to_update.subcategory == new_subcategory


def test_delete_product_by_admin(admin_user_client):
    product = ProductFactory()
    url = reverse('product-detail', kwargs={'pk': product.pk})
    response = admin_user_client.delete(url)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert Product.objects.count() == 0


def test_delete_product_by_regular(authenticated_user_client):
    product = ProductFactory()
    url = reverse('product-detail', kwargs={'pk': product.pk})
    response = authenticated_user_client.delete(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert Product.objects.count() == 1 # El producto no debe ser eliminado


# --- Test para el filtro de subcategorías por categoría (usando datos de fixture) ---
def test_filter_subcategories_by_category_from_fixture(api_client):
    # Las categorías y subcategorías ya están cargadas por la fixture autouse
    # Asumimos que "Electrónica" tiene pk=1 (o obtenlo por nombre)
    electronica_category = Category.objects.get(name="Electrónica")
    
    url_cat1 = reverse('subcategory-list') + f'?category={electronica_category.id}'
    response_cat1 = api_client.get(url_cat1)
    assert response_cat1.status_code == status.HTTP_200_OK
    
    results = response_cat1.data.get('results', [])
    assert len(results) == 2 # Esperamos "Teléfonos Móviles" y "Portátiles" para Electrónica
    subcat_names_cat1 = {item['name'] for item in results} # Usar un set para comparación fácil
    assert "Teléfonos Móviles" in subcat_names_cat1
    assert "Portátiles" in subcat_names_cat1

    # Probar con otra categoría de la fixture
    ropa_category = Category.objects.get(name="Ropa")
    url_cat2 = reverse('subcategory-list') + f'?category={ropa_category.id}'
    response_cat2 = api_client.get(url_cat2)
    assert response_cat2.status_code == status.HTTP_200_OK
    results_cat2 = response_cat2.data.get('results', [])
    assert len(results_cat2) == 2 # Esperamos "Camisetas" y "Pantalones" para Ropa
    subcat_names_cat2 = {item['name'] for item in results_cat2}
    assert "Camisetas" in subcat_names_cat2
    assert "Pantalones" in subcat_names_cat2


    # Probar obtener todas las subcategorías
    url_all = reverse('subcategory-list')
    response_all = api_client.get(url_all)
    assert response_all.status_code == status.HTTP_200_OK
    # El número total de subcategorías debe coincidir con tu fixture
    assert len(response_all.data.get('results', [])) == Subcategory.objects.count()
    assert len(response_all.data.get('results', [])) == 5 # Según el JSON de ejemplo