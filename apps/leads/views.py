from rest_framework import viewsets

from .models import Lead
from .serializers import LeadSerializer


class LeadViewSet(viewsets.ModelViewSet):
    """
    CRUD completo de Leads. Permite filtrar por
    ?status=<status>, ?source=<source>, ?assigned_to=<id>.

    La conversión de un Lead en Contacto/Empresa/Oportunidad es
    lógica de negocio que se agrega en la Fase 3 — este ViewSet
    todavía no la incluye.
    """

    queryset = Lead.objects.select_related("assigned_to").all()
    serializer_class = LeadSerializer
    search_fields = ("title", "name", "email", "company")
    filterset_fields = ("status", "source", "assigned_to")
    ordering_fields = ("created_at", "status")

    def perform_create(self, serializer):
        if serializer.validated_data.get("assigned_to") is None:
            serializer.save(assigned_to=self.request.user)
        else:
            serializer.save()
