from rest_framework import viewsets

from core.tenancy import TenantScopedViewSetMixin

from .models import Opportunity, PipelineStage
from .serializers import OpportunitySerializer, PipelineStageSerializer


class PipelineStageViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    """
    CRUD de etapas del pipeline. Configurable, tal como pide el
    punto 9 del documento (no hardcodeado). Cada cliente tiene las suyas.
    """

    queryset = PipelineStage.objects.all()
    serializer_class = PipelineStageSerializer
    filterset_fields = ("is_active",)
    ordering_fields = ("sequence", "name")
    pagination_class = None


class OpportunityViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    """
    CRUD completo de Oportunidades. Permite filtrar por
    ?company=<id>, ?stage=<id>, ?assigned_to=<id>.
    """

    queryset = Opportunity.objects.select_related(
        "company", "contact", "stage", "assigned_to"
    ).all()
    serializer_class = OpportunitySerializer
    search_fields = ("name", "description", "company__name")
    filterset_fields = ("company", "contact", "stage", "assigned_to")
    ordering_fields = ("name", "created_at", "amount", "expected_closing_date")

    def get_create_defaults(self, serializer):
        if serializer.validated_data.get("assigned_to") is None:
            return {"assigned_to": self.request.user}
        return {}
