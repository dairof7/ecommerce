from pathlib import Path
import os
from decimal import Decimal # Si no lo tienes
from dotenv import load_dotenv # pip install python-dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.path.join(BASE_DIR, '.env'))
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() in ['true', '1', 't']
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True # Redirige todas las solicitudes no seguras (HTTP) a HTTPS a nivel de Django
    SESSION_COOKIE_SECURE = True # Envía cookies de sesión solo sobre HTTPS
    CSRF_COOKIE_SECURE = True    # Envía cookies CSRF solo sobre HTTPS

ALLOWED_HOSTS_STRING = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STRING.split(',')]

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',  # Opcional: Autenticación por token
    'corsheaders', #Para evitar errores de CORS
    'accounts',
    'products',
    'inventory',
    'carts',
    'sales',
    'marketing',
    'django_filters', # Para filtros avanzados
    'drf_spectacular',
    'rest_framework_simplejwt.token_blacklist',
    'django_celery_results',
]

SHOP_COMPANY_NAME = os.environ.get('SHOP_COMPANY_NAME', default='Mi Tienda S.A.S.')
SHOP_COMPANY_NIT = os.environ.get('SHOP_COMPANY_NIT', default='000.000.000-0')
SHOP_SELLER_NAME = os.environ.get('SHOP_SELLER_NAME', default='Nombre del Vendedor')
SHOP_SELLER_ID = os.environ.get('SHOP_SELLER_ID', default='00000000')
SHOP_ADDRESS = os.environ.get('SHOP_ADDRESS', default='Dirección no especificada')
SHOP_PHONE = os.environ.get('SHOP_PHONE', default='(000) 000-0000')
SHOP_EMAIL = os.environ.get('SHOP_EMAIL', default='contacto@mitienda.com')
SHOP_LOGO_URL = os.environ.get('SHOP_LOGO_URL', default='')
# Los valores se leen del .env
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', default='tu_email@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD') # Contraseña de Aplicación de Gmail

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
# Opcional, si quieres usar django-celery-results:
# CELERY_RESULT_BACKEND = 'django-db'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Bogota' # Ajusta a tu zona horaria

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ecommerce.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ecommerce.wsgi.application'


DJANGO_CORS_ALLOWED_ORIGINS_STR = os.environ.get('DJANGO_CORS_ALLOWED_ORIGINS', 'http://localhost:5173,http://localhost:8000')
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in DJANGO_CORS_ALLOWED_ORIGINS_STR.split(',') if origin.strip()]

DJANGO_CSRF_TRUSTED_ORIGINS_STR = os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', 'http://localhost:5173,http://localhost:8000')
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in DJANGO_CSRF_TRUSTED_ORIGINS_STR.split(',') if origin.strip()]

# CORS_ALLOWED_ORIGINS = [origin.strip() for origin in os.environ.get('DJANGO_CORS_ALLOWED_ORIGINS', 'http://localhost:5173').split(',')]
CORS_ALLOW_CREDENTIALS = True

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

DATABASES = {
    'default': {
        'ENGINE': os.environ.get('SQL_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.environ.get('POSTGRES_DB'), # Para e-commerce, debería ser POSTGRES_DB
        'USER': os.environ.get('POSTGRES_USER'), # POSTGRES_USER
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD'), # POSTGRES_PASSWORD
        'HOST': os.environ.get('POSTGRES_HOST', 'db'), # db_ecommerce
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly'
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 18,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Your Project API',
    'DESCRIPTION': 'Your project description',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    # OTHER SETTINGS
}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'es-co'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

USE_L10N = True

USE_FORMATTING = True

THOUSAND_SEPARATOR = '.'
DECIMAL_SEPARATOR = ',' # Aunque no mostrarás decimales, es bueno definirlo.
NUMBER_GROUPING = 3 # Agrupar cada 3 dígitos.

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'mediafiles')
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=11120),  # 1 hora en segundos
    # 'REFRESH_TOKEN_LIFETIME': 604800,  # 7 días en segundos
    # 'REFRESH_TOKEN_LIFETIME': 604800,  # 7 días en segundos
}

AUTH_USER_MODEL = 'accounts.CustomUser'