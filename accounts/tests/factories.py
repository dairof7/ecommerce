import factory
from factory.django import DjangoModelFactory
from faker import Faker
from django.contrib.auth import get_user_model # Para obtener el modelo User
from accounts.models import UserProfile

fake = Faker()
User = get_user_model() # Obtener el modelo User activo

class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        # Si quieres que se cree el objeto en la BD al llamar a UserFactory()
        # y evitar duplicados por username:
        django_get_or_create = ('username',)
        skip_postgeneration_save = True

    # Usar secuencia para asegurar usernames únicos si no usas django_get_or_create
    # o si creas muchos sin guardar.
    username = factory.Sequence(lambda n: f"{fake.user_name().lower().replace(' ', '_')}{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')

    # Por defecto, crea un usuario activo sin privilegios de staff/superuser
    is_staff = False
    is_superuser = False
    is_active = True

    # Importante: Para crear usuarios con contraseña, Django necesita un tratamiento especial.
    # factory_boy no setea la contraseña directamente con user.password = "..."
    # porque Django la hashea.
    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            # Si solo se está construyendo la instancia (build), no se hace nada con la contraseña.
            return
        
        # Si se pasó una contraseña explícitamente (ej. UserFactory(password="micontraseña"))
        if extracted:
            self.set_password(extracted)
        else:
            # Si no, genera una contraseña por defecto
            self.set_password(fake.password(length=12))
        
        # Es importante guardar el usuario de nuevo después de setear la contraseña
        # si la factoría no lo hace automáticamente después de post_generation.
        # Sin embargo, DjangoModelFactory usualmente guarda después de todo.
        # Si tienes problemas, puedes añadir self.save() aquí.
        self.save()

    # También puedes crear variaciones de la factoría, por ejemplo, para administradores:
    # class AdminUserFactory(UserFactory):
    #     is_staff = True
    #     is_superuser = True


class UserProfileFactory(DjangoModelFactory):
    class Meta:
        model = UserProfile

    # Asocia el perfil a un usuario creado por UserFactory
    # Usar SubFactory asegura que se cree un User si no se proporciona uno.
    user = factory.SubFactory(UserFactory)
    
    address = factory.Faker('address')
    document = factory.Faker('ssn') # O un generador más específico para tu tipo de documento
    phone = factory.Faker('phone_number')

    # Si UserFactory crea un UserProfile automáticamente (como en tu vista de registro),
    # podrías necesitar ajustar esto para evitar crear dos perfiles,
    # o asegurarte de que UserFactory no cree el perfil si se está usando UserProfileFactory.
    # Una forma es:
    # @factory.post_generation
    # def ensure_single_profile(self, create, extracted, **kwargs):
    #     if create:
    #         # Si ya existe un perfil para este usuario (creado por UserFactory),
    #         # actualiza ese en lugar de crear uno nuevo.
    #         # Esto es más complejo y depende de tu lógica exacta.
    #         # Por ahora, asumimos que UserFactory NO crea UserProfile automáticamente
    #         # O que la lógica de UserProfileFactory es la principal para perfiles.
    #         pass