"""
Panel Solvis: administración de clientes (tenants) y sus usuarios desde el
propio CRM. Solo para el personal de Solvis (is_staff).

GET/POST   /api/backoffice/tenants/                 clientes
GET/PATCH  /api/backoffice/tenants/{id}/
POST       /api/backoffice/tenants/{id}/suspend/     suspende y cierra todas sus sesiones
POST       /api/backoffice/tenants/{id}/activate/
GET/POST   /api/backoffice/tenants/{id}/users/       usuarios del cliente
PATCH      /api/backoffice/users/{id}/
POST       /api/backoffice/users/{id}/set-password/  {password?} (vacío = se genera una)
POST       /api/backoffice/users/{id}/logout/        cierra todas sus sesiones
"""
import secrets

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Max, Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.companies.models import Company
from apps.leads.models import Lead
from apps.opportunities.models import Opportunity
from apps.tenants.models import Tenant
from core.exceptions import BusinessRuleError

from .serializers import BackofficeTenantSerializer, BackofficeUserSerializer

User = get_user_model()
PASSWORD_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"


def generate_password():
    """Contraseña legible: 4 grupos de 4, sin caracteres que se confunden (l/I, O/0)."""
    return "-".join("".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(4)) for _ in range(4))


def close_sessions(users):
    """Invalida los refresh tokens; el access vigente vence solo (o lo corta la suspensión)."""
    tokens = OutstandingToken.objects.filter(user__in=users).exclude(blacklistedtoken__isnull=False)
    BlacklistedToken.objects.bulk_create([BlacklistedToken(token=t) for t in tokens], ignore_conflicts=True)
    return len(tokens)


def count_for(model, tenant_ids):
    rows = model.objects.filter(tenant_id__in=tenant_ids).values("tenant_id").annotate(n=Count("id"))
    return {r["tenant_id"]: r["n"] for r in rows}


class TenantBackofficeViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                              mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = (IsAdminUser,)
    serializer_class = BackofficeTenantSerializer
    search_fields = ("name", "slug")
    ordering_fields = ("name", "created_at")
    pagination_class = None

    def get_queryset(self):
        return Tenant.objects.annotate(
            users_count=Count("users", distinct=True),
            active_users=Count("users", filter=Q(users__is_active=True), distinct=True),
            last_login=Max("users__last_login"),
        ).order_by("name")

    def _with_counts(self, tenants):
        ids = [t.id for t in tenants]
        counts = {"companies_count": count_for(Company, ids), "leads_count": count_for(Lead, ids),
                  "opportunities_count": count_for(Opportunity, ids)}
        for t in tenants:
            for key, by_tenant in counts.items():
                setattr(t, key, by_tenant.get(t.id, 0))
        return tenants

    def list(self, request, *args, **kwargs):
        tenants = self._with_counts(list(self.filter_queryset(self.get_queryset())))
        return Response(self.get_serializer(tenants, many=True).data)

    def retrieve(self, request, *args, **kwargs):
        tenant = self._with_counts([self.get_object()])[0]
        return Response(self.get_serializer(tenant).data)

    def perform_update(self, serializer):
        was_active = serializer.instance.is_active
        tenant = serializer.save()
        if was_active and not tenant.is_active:
            close_sessions(tenant.users.all())

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        tenant = self.get_object()
        if tenant.users.filter(pk=request.user.pk).exists():
            raise BusinessRuleError("No podés suspender tu propia empresa.", "self_tenant")
        tenant.is_active = False
        tenant.save(update_fields=["is_active"])
        closed = close_sessions(tenant.users.all())
        return Response({"is_active": False, "sessions_closed": closed})

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        tenant = self.get_object()
        tenant.is_active = True
        tenant.save(update_fields=["is_active"])
        return Response({"is_active": True})

    @action(detail=True, methods=["get", "post"])
    def users(self, request, pk=None):
        tenant = self.get_object()
        if request.method == "GET":
            users = tenant.users.order_by("first_name", "username")
            return Response(BackofficeUserSerializer(users, many=True).data)
        serializer = BackofficeUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data.pop("password", "") or generate_password()
        with transaction.atomic():
            user = serializer.save(tenant=tenant)
            user.set_password(password)
            user.save(update_fields=["password"])
        data = BackofficeUserSerializer(user).data
        data["generated_password"] = password if not request.data.get("password") else None
        return Response(data, status=status.HTTP_201_CREATED)


class UserBackofficeViewSet(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = (IsAdminUser,)
    serializer_class = BackofficeUserSerializer
    queryset = User.objects.select_related("tenant")

    def perform_update(self, serializer):
        serializer.validated_data.pop("password", None)
        if serializer.instance == self.request.user and serializer.validated_data.get("is_active") is False:
            raise BusinessRuleError("No podés desactivar tu propio usuario.", "self_user")
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
