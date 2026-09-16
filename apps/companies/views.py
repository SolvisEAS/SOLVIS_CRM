from rest_framework import viewsets

from .models import Company
from .serializers import CompanySerializer


class CompanyViewSet(viewsets.ModelViewSet):
    """
    CRUD completo de Empresas.

    GET    /api/companies/          -> listar (con búsqueda, filtros, orden)
    POST   /api/companies/          -> crear
    GET    /api/companies/{id}/     -> detalle
    PUT    /api/companies/{id}/     -> actualizar completo
    PATCH  /api/companies/{id}/     -> actualizar parcial
    DELETE /api/companies/{id}/     -> eliminar
    """

    queryset = Company.objects.select_related("owner").all()
    serializer_class = CompanySerializer
    search_fields = ("name", "email", "city", "country")
    filterset_fields = ("owner", "country", "city")
    ordering_fields = ("name", "created_at")

    def perform_create(self, serializer):
        # Si no se especifica owner explícitamente, se asigna quien crea.
        if serializer.validated_data.get("owner") is None:
            serializer.save(owner=self.request.user)
        else:
            serializer.save()
