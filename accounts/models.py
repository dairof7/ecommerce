from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _ # Para traducciones

class CustomUser(AbstractUser):
    # Puedes añadir campos adicionales aquí si lo necesitas
    # email ya está definido en AbstractUser, pero lo sobrescribiremos para hacerlo único y no blank.
    email = models.EmailField(_('email address'), unique=True) # Hacerlo único es una buena práctica

    # Si quieres usar email como USERNAME_FIELD:
    # USERNAME_FIELD = 'email'
    # REQUIRED_FIELDS = ['username'] # username seguiría siendo necesario si no lo eliminas
    # O si solo quieres email como campo principal y username opcional o no usado para login:
    # USERNAME_FIELD = 'email'
    # REQUIRED_FIELDS = [] # Si el username ya no es necesario para crear el usuario

    def __str__(self):
        return self.username # o self.email si es el campo principal

class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile', primary_key=True)  # Extiende el modelo User
    address = models.CharField(max_length=255, blank=True, default='')
    document = models.CharField(max_length=20, blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    # email = models.EmailField(_('email address'), unique=True)
    # def __str__(self):
    #     return self.user.username
    def __str__(self):
        if hasattr(self.user, 'email'): # Verificar si el modelo de usuario tiene email
            return f"Profile for {self.user.email}"
        return f"Profile for {self.user.username}" # Fallback a username