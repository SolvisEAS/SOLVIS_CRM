from django.db.models import Count
from rest_framework import viewsets

from core.tenancy import TenantScopedViewSetMixin

from .models import Company
from .serializers import CompanySerializer


class CompanyViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    """
    CRUD completo de Empresas (solo las del cliente del usuario).

    GET    /api/companies/          -> listar (con búsqueda, filtros, orden)
    POST   /api/companies/          -> crear
    GET    /api/companies/{id}/     -> detalle
    PUT    /api/companies/{id}/     -> actualizar completo
    PATCH  /api/companies/{id}/     -> actualizar parcial
    DELETE /api/companies/{id}/     -> eliminar
    """

    queryset = Company.objects.select_related("owner").annotate(
        contacts_count=Count("contacts", distinct=True),
        opportunities_count=Count("opportunities", distinct=True),
    )
    serializer_class = CompanySerializer
    search_fields = ("name", "email", "city", "country")
    filterset_fields = ("owner", "country", "city")
    ordering_fields = ("name", "city", "country", "created_at")

    def get_create_defaults(self, serializer):
        # Si no se especifica owner explícitamente, se asigna quien crea.
        if serializer.validated_data.get("owner") is None:
            return {"owner": self.request.user}
        return {}
