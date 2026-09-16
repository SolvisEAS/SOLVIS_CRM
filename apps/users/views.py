from django.contrib.auth import get_user_model
from rest_framework import generics, permissions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import UserRegistrationSerializer, UserSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    POST /api/users/register/

    Endpoint público para crear un nuevo usuario. No requiere
    autenticación (a diferencia del resto de la API).
    """

    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = (permissions.AllowAny,)


class MeView(APIView):
    """
    GET /api/users/me/

    Devuelve el usuario autenticado actual. Este es el endpoint
    "canario": si esto funciona, el flujo completo de JWT
    (login -> access token -> request autenticado) está funcionando.
    """

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request: Request) -> Response:
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
