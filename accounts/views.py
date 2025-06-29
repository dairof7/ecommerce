# accounts/views.py
"""
API Views for user account management.

Provides endpoints for user registration and for retrieving/updating
user profiles.
"""
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserProfile
from .serializers import UserSerializer, UserProfileSerializer

# Standard practice to get the active User model.
User = get_user_model()


class UserCreate(generics.CreateAPIView):
    """
    Handle user registration.
    
    Creates a new user and an associated profile, then returns JWT
    authentication tokens for immediate use.
    
    Permissions:
      - AllowAny: Any user (authenticated or not) can register.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        """
        Creates a user, profile, and returns JWT tokens.
        
        Overrides the default post method to add token generation to the
        response upon successful user creation.

        Returns:
            - Response (201 Created): Contains 'refresh' and 'access' tokens.
            - Response (400 Bad Request): Contains validation errors.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        UserProfile.objects.create(user=user)
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
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