import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken # Para verificar tokens si es necesario

from .factories import UserFactory, UserProfileFactory
from accounts.models import UserProfile

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()

# --- Tests para el endpoint de Registro de Usuario (POST /api/accounts/register/) ---
def test_user_registration_success(api_client):
    url = reverse('register') # Asumiendo que tu URL de registro se llama 'register'
    user_data = {
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'StrongPassword123'
    }
    response = api_client.post(url, user_data, format='json')

    assert response.status_code == status.HTTP_201_CREATED
    assert User.objects.count() == 1
    assert User.objects.get(username='newuser').email == 'newuser@example.com'
    
    # Verifica que se creó el UserProfile asociado
    assert UserProfile.objects.count() == 1
    assert UserProfile.objects.get(user__username='newuser') is not None

    # Verifica que la respuesta contiene tokens JWT
    assert 'access' in response.data
    assert 'refresh' in response.data

def test_user_registration_missing_fields(api_client):
    url = reverse('register')
    invalid_data = {
        'username': 'testuser'
        # Falta email y password
    }
    response = api_client.post(url, invalid_data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'email' in response.data
    assert 'password' in response.data

def test_user_registration_duplicate_username(api_client):
    UserFactory(username='existinguser') # Crea un usuario existente
    url = reverse('register')
    duplicate_data = {
        'username': 'existinguser',
        'email': 'newemail@example.com',
        'password': 'password123'
    }
    response = api_client.post(url, duplicate_data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'username' in response.data # O el mensaje de error específico de tu serializador

# --- Tests para el endpoint de Login (Obtener Token JWT) (POST /api/token/) ---
def test_user_login_get_token_success(api_client):
    password = 'SecurePassword123'
    user = UserFactory(username='loginuser', password=password) # Crea usuario con contraseña
    url = reverse('token_obtain_pair') # URL de SimpleJWT para obtener tokens
    login_data = {
        'username': 'loginuser',
        'password': password
    }
    response = api_client.post(url, login_data, format='json')
    assert response.status_code == status.HTTP_200_OK
    assert 'access' in response.data
    assert 'refresh' in response.data
    
    # Opcional: Decodificar el token para verificar claims (más avanzado)
    # from rest_framework_simplejwt.utils import decode_jwt
    # access_token_payload = decode_jwt(response.data['access'])
    # assert access_token_payload['user_id'] == user.id

def test_user_login_invalid_credentials(api_client):
    UserFactory(username='loginuser', password='password123')
    url = reverse('token_obtain_pair')
    invalid_login_data = {
        'username': 'loginuser',
        'password': 'WrongPassword'
    }
    response = api_client.post(url, invalid_login_data, format='json')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED # SimpleJWT devuelve 401 para credenciales inválidas
    assert 'detail' in response.data # Debería haber un mensaje de error

# --- Tests para el endpoint de Perfil de Usuario (GET, PUT /api/accounts/profile/) ---
@pytest.fixture
def authenticated_client_with_profile():
    # Crea un usuario y su perfil, y un cliente autenticado para ese usuario
    user_profile = UserProfileFactory() # Esto crea un User y un UserProfile
    client = APIClient()
    client.force_authenticate(user=user_profile.user)
    return client, user_profile.user # Devuelve el cliente y el usuario

def test_get_user_profile_success(authenticated_client_with_profile):
    client, user = authenticated_client_with_profile
    url = reverse('profile') # Asumiendo que tu URL de perfil se llama 'profile'
    
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data['user'] == user.username # O como sea que tu UserProfileSerializer muestre el user
    assert response.data['address'] is not None # Verifica que los campos del perfil estén presentes

def test_get_user_profile_unauthenticated(api_client):
    url = reverse('profile')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED # O 403 si IsAuthenticatedOrReadOnly y es GET

def test_update_user_profile_success(authenticated_client_with_profile):
    client, user = authenticated_client_with_profile
    url = reverse('profile')
    
    profile_data_to_update = {
        'address': '123 New Address St',
        'phone': '555-0123',
        'document': 'NEWDOC123',
        'email': 'emi12321@gmail.com'
    }
    response = client.put(url, profile_data_to_update, format='json') # Usar PUT para actualización completa o PATCH para parcial

    assert response.status_code == status.HTTP_200_OK
    user.profile.refresh_from_db() # Recarga el perfil desde la BD
    assert user.profile.address == profile_data_to_update['address']
    assert user.profile.phone == profile_data_to_update['phone']

def test_update_user_profile_unauthenticated(api_client):
    # Crear un perfil para que exista algo que intentar actualizar
    user_profile = UserProfileFactory()
    url = reverse('profile') # Esta URL generalmente no toma PK porque es "mi perfil"
    
    profile_data_to_update = {'address': 'Attempted Update St'}
    response = api_client.put(url, profile_data_to_update, format='json')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

# --- Tests para el endpoint de Logout (Blacklist Token) (POST /api/logout/) ---
def test_user_logout_success(authenticated_client_with_profile):
    client, user = authenticated_client_with_profile
    
    # 1. Obtener un token de refresco para el usuario (simulando un login previo)
    # Esto es un poco artificial aquí porque authenticated_client_with_profile ya está "autenticado"
    # para el cliente de prueba de DRF, pero necesitamos un token de refresco real.
    refresh = RefreshToken.for_user(user)
    refresh_token_str = str(refresh)

    url_logout = reverse('token_blacklist') # URL para invalidar el token
    logout_data = {
        'refresh': refresh_token_str
    }
    response = client.post(url_logout, logout_data, format='json')
    
    assert response.status_code == status.HTTP_200_OK # SimpleJWT devuelve 200 para blacklisting exitoso

    # Opcional: Intentar usar el token de refresco invalidado para obtener un nuevo token de acceso
    # Debería fallar.
    # url_refresh = reverse('token_refresh')
    # refresh_response = client.post(url_refresh, {'refresh': refresh_token_str}, format='json')
    # assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
    # assert 'token_not_valid' in refresh_response.data.get('code', '')

def test_user_logout_invalid_refresh_token(api_client): # Usar cliente no autenticado es más realista aquí
    url_logout = reverse('token_blacklist')
    logout_data = {
        'refresh': 'untoken.de.refresco.invalido'
    }
    response = api_client.post(url_logout, logout_data, format='json')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED # O 401 si el token es inválido en formato
    assert 'token_not_valid' in response.data.get('code', []) or 'refresh' in response.data
