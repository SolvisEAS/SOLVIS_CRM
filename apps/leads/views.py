from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.exceptions import BusinessRuleError
from core.tenancy import TenantScopedViewSetMixin

from .models import Lead
from .serializers import LeadConvertSerializer, LeadSerializer
from .services import convert_lead


class LeadViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    """
    CRUD completo de Leads. Permite filtrar por
    ?status=<status>, ?source=<source>, ?assigned_to=<id>.

    POST /api/leads/{id}/convert/ convierte el Lead en Empresa +
    Contacto (+ Oportunidad opcional), como el "Convertir" de Zoho CRM.
    """

    queryset = Lead.objects.select_related("assigned_to").all()
    serializer_class = LeadSerializer
    search_fields = ("title", "name", "email", "phone", "company")
    filterset_fields = ("status", "source", "assigned_to")
    ordering_fields = ("created_at", "status", "name", "company")
    timeline_type = "lead"
    tracked_fields = {"status": "Estado", "assigned_to": "Propietario", "source": "Origen",
                      "title": "Título", "company": "Empresa", "email": "Correo", "phone": "Teléfono"}

    def get_create_defaults(self, serializer):
        if serializer.validated_data.get("assigned_to") is None:
            return {"assigned_to": self.request.user}
        return {}

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        lead = self.get_object()
        if lead.status == Lead.Status.CONVERTIDO:
            raise BusinessRuleError("Este lead ya fue convertido.", "lead_already_converted")
        params = LeadConvertSerializer(data=request.data)
        params.is_valid(raise_exception=True)
        company, contact, opportunity = convert_lead(lead, request.user, **params.validated_data)
        return Response(
            {
                "lead": LeadSerializer(lead, context=self.get_serializer_context()).data,
                "company": company.id,
                "contact": contact.id,
                "opportunity": opportunity.id if opportunity else None,
            },
            status=status.HTTP_200_OK,
        )
