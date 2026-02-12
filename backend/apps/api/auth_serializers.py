from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from apps.api.serializers import UserSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializer personalizado para incluir información del usuario en la respuesta de login
    """
    
    def validate(self, attrs):
        # Obtener los tokens usando el serializer padre
        data = super().validate(attrs)
        
        # Agregar información del usuario
        user_serializer = UserSerializer(self.user)
        data['user'] = user_serializer.data
        
        return data


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer para la respuesta de login
    """
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()
