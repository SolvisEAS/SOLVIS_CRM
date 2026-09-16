from rest_framework import viewsets

from .models import Opportunity, PipelineStage
from .serializers import OpportunitySerializer, PipelineStageSerializer


class PipelineStageViewSet(viewsets.ModelViewSet):
    """
    CRUD de etapas del pipeline. Configurable, tal como pide el
    punto 9 del documento (no hardcodeado).
    """

    queryset = PipelineStage.objects.all()
    serializer_class = PipelineStageSerializer
    ordering_fields = ("sequence", "name")


class OpportunityViewSet(viewsets.ModelViewSet):
    """
    CRUD completo de Oportunidades. Permite filtrar por
    ?company=<id>, ?stage=<id>, ?assigned_to=<id>.
    """

    queryset = Opportunity.objects.select_related(
        "company", "contact", "stage", "assigned_to"
    ).all()
    serializer_class = OpportunitySerializer
    search_fields = ("name", "description")
    filterset_fields = ("company", "contact", "stage", "assigned_to")
    ordering_fields = ("created_at", "amount", "expected_closing_date")

    def perform_create(self, serializer):
        if serializer.validated_data.get("assigned_to") is None:
            serializer.save(assigned_to=self.request.user)
        else:
            serializer.save()
