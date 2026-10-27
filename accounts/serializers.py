from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import UserProfile
from django.db import transaction

User = get_user_model()

# Serializador para los datos del perfil que se recibirán anidados
class UserProfileDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        # Campos que el usuario proporcionará para el perfil
        # Excluimos 'user' porque se manejará en el serializador padre.
        fields = ('address', 'document', 'phone')

# Serializador principal para el proceso de registro
class UserRegistrationSerializer(serializers.ModelSerializer):
    # Campo para el perfil anidado, es escribible y opcional
    profile = UserProfileDataSerializer(required=False)

    class Meta:
        model = User
        # Campos del User que se esperan en el registro, incluyendo first_name y last_name
        fields = ('id', 'username', 'email', 'password', 'first_name', 'last_name', 'profile')
        extra_kwargs = {
            'password': {'write_only': True},
            'id': {'read_only': True}
        }

    def create(self, validated_data):
        # Usar una transacción para asegurar que o se crea el usuario Y el perfil, o no se crea nada.
        with transaction.atomic():
            # Extraer los datos del perfil del validated_data
            profile_data = validated_data.pop('profile', None)

            # Extraer first_name y last_name para pasarlos a create_user
            first_name = validated_data.pop('first_name', '')
            last_name = validated_data.pop('last_name', '')
            
            # Crear el User usando el manager create_user para hashear la contraseña correctamente
            user = User.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                **validated_data # Esto pasará username, email, password
            )

            # Crear el UserProfile con los datos del perfil si se proporcionaron
            if profile_data:
                UserProfile.objects.create(user=user, **profile_data)
            else:
                # Si el perfil es opcional y no se envían datos,
                # Django creará un perfil vacío si tienes una señal post_save,
                # o puedes crearlo explícitamente aquí si es un requisito.
                UserProfile.objects.create(user=user)

        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
class UserProfileSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    email = serializers.ReadOnlyField(source='user.email')
    is_staff = serializers.ReadOnlyField(source='user.is_staff')
    
    class Meta:
        model = UserProfile
        fields = ('user', 'address', 'document', 'phone', 'is_staff', 'email')

class UserSearchSerializer(serializers.ModelSerializer):
    """
    Serializador simplificado para los resultados de búsqueda de usuarios.
    Devuelve solo la información necesaria para el POS.
    """
    # Obtener datos del perfil directamente
    address = serializers.CharField(source='profile.address', read_only=True)
    document = serializers.CharField(source='profile.document', read_only=True)
    phone = serializers.CharField(source='profile.phone', read_only=True)
    full_name = serializers.SerializerMethodField()
    class Meta:
        model = User # O settings.AUTH_USER_MODEL
        fields = [
            'id',
            'full_name',
            'first_name',
            'last_name',
            'email',
            'username', # Si todavía lo usas
            'address',
            'document',
            'phone'
        ]
    def get_full_name(self, obj):
        # Construye un nombre completo. Si no hay, usa username. Si no, usa email.
        name = f"{obj.first_name} {obj.last_name}".strip()
        if name:
            return name
        if obj.username:
            return obj.username
        return obj.email

class POSCustomerCreateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    email = serializers.EmailField(required=True)
    document = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    address = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    password = serializers.CharField(max_length=128, required=False, allow_blank=True, default='')

    def validate_email(self, value):
        email = value.lower().strip()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("Ya existe un usuario con este correo electrónico.")
        return email

    def create(self, validated_data):
        email = validated_data['email']
        first_name = validated_data.get('first_name', '').strip()
        last_name = validated_data.get('last_name', '').strip()
        document = validated_data.get('document', '').strip()
        phone = validated_data.get('phone', '').strip()
        address = validated_data.get('address', '').strip()
        password = validated_data.get('password', '').strip()

        # Generar contraseña por defecto si no se proporcionó
        if not password:
            if document and len(document) >= 6:
                password = document
            elif phone and len(phone) >= 6:
                password = phone
            else:
                import secrets
                import string
                alphabet = string.ascii_letters + string.digits
                password = ''.join(secrets.choice(alphabet) for _ in range(10))

        # Generar username único basado en email
        base_username = email.split('@')[0][:100]
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username[:90]}_{counter}"
            counter += 1

        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_staff=False,
                is_superuser=False,
                is_active=True
            )
            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    'document': document,
                    'phone': phone,
                    'address': address
                }
            )
        return user