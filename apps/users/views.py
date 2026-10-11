from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.backoffice.views import close_sessions, generate_password
from core.exceptions import BusinessRuleError
from core.permissions import IsAdministrador
from core.tenancy import user_tenant_id

from .serializers import UserAdminUpdateSerializer, UserListSerializer, UserRegistrationSerializer, UserSerializer

User = get_user_model()


class UserViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                  mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """
    GET  /api/users/          -> usuarios del mismo cliente (para "Asignado a")
    GET  /api/users/{id}/     -> detalle
    POST /api/users/          -> alta de usuario (solo ADMINISTRADOR, en su propio cliente)
    POST /api/users/register/ -> alias de lo anterior (compatibilidad Fase 1)
    PATCH /api/users/{id}/    -> editar nombre, correo, rol o activo (solo ADMINISTRADOR)
    POST /api/users/{id}/set-password/ y /logout/ -> igual que en el Panel Solvis,
         pero solo para usuarios del propio cliente (solo ADMINISTRADOR)

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
        if self.action == "create":
            return UserRegistrationSerializer
        if self.action in ("update", "partial_update"):
            return UserAdminUpdateSerializer
        return UserListSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]
        return [IsAdministrador()]

    def perform_create(self, serializer):
        serializer.save(tenant_id=user_tenant_id(self.request.user))

    def get_object(self):
        user = super().get_object()
        # Las cuentas del personal de Solvis solo las toca el propio personal de Solvis.
        if self.action not in ("retrieve",) and user.is_staff and not self.request.user.is_staff:
            raise BusinessRuleError("Este usuario lo administra Solvis.", "staff_user")
        return user

    def perform_update(self, serializer):
        if serializer.instance == self.request.user and (
            serializer.validated_data.get("is_active") is False
            or serializer.validated_data.get("role", User.Roles.ADMINISTRADOR) != User.Roles.ADMINISTRADOR
        ):
            raise BusinessRuleError("No podés desactivarte ni quitarte el rol de administrador a vos mismo.", "self_user")
        user = serializer.save()
        if not user.is_active:
            close_sessions([user])

    @action(detail=True, methods=["post"], url_path="set-password")
    def set_password(self, request, pk=None):
        user = self.get_object()
        typed = (request.data.get("password") or "").strip()
        if typed and len(typed) < 8:
            raise BusinessRuleError("La contraseña tiene que tener al menos 8 caracteres.", "short_password")
        password = typed or generate_password()
        user.set_password(password)
        user.save(update_fields=["password"])
        if request.data.get("logout", True):
            close_sessions([user])
        return Response({"generated_password": None if typed else password})

    @action(detail=True, methods=["post"])
    def logout(self, request, pk=None):
        return Response({"sessions_closed": close_sessions([self.get_object()])})


class ChangeMyPasswordView(APIView):
    """POST /api/users/me/password/ {current_password, new_password} — cada uno cambia la suya."""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request: Request) -> Response:
        current = request.data.get("current_password") or ""
        new = request.data.get("new_password") or ""
        if not request.user.check_password(current):
            raise BusinessRuleError("La contraseña actual no es correcta.", "wrong_password")
        try:
            validate_password(new, request.user)
        except DjangoValidationError as exc:
            raise BusinessRuleError(" ".join(exc.messages), "weak_password")
        request.user.set_password(new)
        request.user.save(update_fields=["password"])
        return Response({"detail": "Contraseña actualizada."})


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
