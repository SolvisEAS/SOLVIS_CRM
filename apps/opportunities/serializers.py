from rest_framework import serializers

from core.tenancy import TenantScopedSerializerMixin

from .models import Opportunity, PipelineStage


class PipelineStageSerializer(TenantScopedSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = PipelineStage
        fields = (
            "id",
            "name",
            "sequence",
            "probability",
            "color",
            "is_won",
            "is_lost",
            "is_active",
        )
        read_only_fields = ("id",)


class OpportunitySerializer(TenantScopedSerializerMixin, serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    contact_name = serializers.SerializerMethodField()
    stage_name = serializers.CharField(source="stage.name", read_only=True)
    stage_color = serializers.CharField(source="stage.color", read_only=True)
    expected_revenue = serializers.SerializerMethodField()
    assigned_to_username = serializers.CharField(
        source="assigned_to.username", read_only=True
    )

    class Meta:
        model = Opportunity
        fields = (
            "id",
            "name",
            "company",
            "company_name",
            "contact",
            "contact_name",
            "amount",
            "probability",
            "expected_closing_date",
            "stage",
            "stage_name",
            "stage_color",
            "expected_revenue",
            "closed_at",
            "assigned_to",
            "assigned_to_username",
            "description",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "closed_at")

    def get_expected_revenue(self, obj):
        """Monto ponderado por la probabilidad (el "Ingreso esperado" de Zoho)."""
        return round(float(obj.amount) * obj.probability / 100, 2)

    def get_contact_name(self, obj):
        if obj.contact:
            return f"{obj.contact.first_name} {obj.contact.last_name}"
        return None
