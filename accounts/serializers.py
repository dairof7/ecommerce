from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import UserProfile

User = get_user_model()

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

    class Meta:
        model = UserProfile
        fields = '__all__'