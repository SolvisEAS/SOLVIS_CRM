from django.contrib.auth import get_user_model
from rest_framework import mixins, permissions, viewsets
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsAdministrador
from core.tenancy import user_tenant_id

from .serializers import UserListSerializer, UserRegistrationSerializer, UserSerializer

User = get_user_model()


class UserViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    GET  /api/users/          -> usuarios del mismo cliente (para "Asignado a")
    GET  /api/users/{id}/     -> detalle
    POST /api/users/          -> alta de usuario (solo ADMINISTRADOR, en su propio cliente)
    POST /api/users/register/ -> alias de lo anterior (compatibilidad Fase 1)

    El registro ya no es público: con varios clientes en el mismo back,
    cada usuario tiene que nacer dentro de un cliente.
    """

    search_fields = ("username", "first_name", "last_name", "email")
    filterset_fields = ("role", "is_active")
    ordering_fields = ("username", "first_name", "date_joined")

    def get_queryset(self):
        tenant_id = user_tenant_id(self.request.user)
        if tenant_id is None:
            return User.objects.none()
        return User.objects.filter(tenant_id=tenant_id).order_by("first_name", "username")

    def get_serializer_class(self):
        return UserRegistrationSerializer if self.action == "create" else UserListSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsAdministrador()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(tenant_id=user_tenant_id(self.request.user))


class MeView(APIView):
    """
    GET /api/users/me/

    Devuelve el usuario autenticado actual con su cliente. El front lo
    usa para saber qué front le corresponde y con qué colores/logo.
    """

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request: Request) -> Response:
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
