from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import api_view, permission_classes
from apps.api.serializers import UserSerializer
from apps.api.auth_serializers import CustomTokenObtainPairSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Vista personalizada para login que incluye información del usuario
    """
    serializer_class = CustomTokenObtainPairSerializer


class CurrentUserView(generics.RetrieveAPIView):
    """
    Vista para obtener los datos del usuario autenticado actual
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """
        Retorna el usuario autenticado actual
        """
        return self.request.user
    
    def retrieve(self, request, *args, **kwargs):
        """
        Personalización de la respuesta para incluir información adicional
        """
        user = self.get_object()
        serializer = self.get_serializer(user)
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def LogoutView(request):
    """
    Vista para logout. Con JWT, solo se necesita limpiar el token en el cliente.
    """
    return Response(
        {'message': 'Logout exitoso'},
        status=status.HTTP_200_OK
    )
