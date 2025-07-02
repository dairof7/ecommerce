# accounts/views.py
"""
API Views for user account management.

Provides endpoints for user registration and for retrieving/updating
user profiles.
"""
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSearchSerializer

from .models import UserProfile
from .serializers import UserRegistrationSerializer, UserProfileSerializer

# Standard practice to get the active User model.
User = get_user_model()


class UserCreate(generics.CreateAPIView):
    """
    Maneja el registro de usuarios, incluyendo datos del perfil.
    """
    queryset = User.objects.all()
    # --- USA EL SERIALIZADOR CORRECTO ---
    serializer_class = UserRegistrationSerializer 
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # El método .save() ahora llama al create() de UserRegistrationSerializer,
        # que se encarga de crear tanto el User como el UserProfile.
        user = serializer.save()
        
        # Ya no necesitas esta línea aquí, porque el serializador ya lo hizo:
        # UserProfile.objects.create(user=user) 
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Usuario registrado exitosamente.',
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            # Opcional: devolver los datos del usuario recién creado
            # 'user': UserRegistrationSerializer(user).data
        }, status=status.HTTP_201_CREATED)


class UserProfileRetrieveUpdate(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update the profile of the currently authenticated user.
    
    Permissions:
      - IsAuthenticated: Only logged-in users can access their own profile.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """
        Return the UserProfile instance for the currently authenticated user.
        
        Ensures users can only view and edit their own profile without needing
        to specify a primary key in the URL.
        """
        # Every user is guaranteed to have a profile due to the logic
        # in the UserCreate view or a post-save signal.
        return self.request.user.profile

class UserSearchView(generics.ListAPIView):
    """
    Vista para que los administradores busquen usuarios registrados.
    Acepta un parámetro de búsqueda 'search'.
    Ej: /api/accounts/user-search/?search=juan@
    """
    serializer_class = UserSearchSerializer
    permission_classes = [permissions.IsAdminUser] # ¡MUY IMPORTANTE! Solo admins
    filter_backends = [filters.SearchFilter]
    
    # Campos en los que se buscará el término
    search_fields = [
        'first_name',
        'last_name',
        'email',
        'username',
        'profile__document', # Buscar en el documento del perfil asociado
        'profile__phone'     # Buscar en el teléfono del perfil asociado
    ]

    def get_queryset(self):
        # Devolver solo usuarios que NO son staff o superusuarios, para encontrar solo clientes.
        # O puedes devolver todos si un admin puede comprar para otro admin.
        # Por ahora, excluimos al personal.
        return User.objects.filter(is_staff=False, is_superuser=False).select_related('profile')