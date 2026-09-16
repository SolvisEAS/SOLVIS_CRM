from rest_framework import serializers

from .models import Opportunity, PipelineStage


class PipelineStageSerializer(serializers.ModelSerializer):
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


class OpportunitySerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    contact_name = serializers.SerializerMethodField()
    stage_name = serializers.CharField(source="stage.name", read_only=True)
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
            "assigned_to",
            "assigned_to_username",
            "description",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_contact_name(self, obj):
        if obj.contact:
            return f"{obj.contact.first_name} {obj.contact.last_name}"
        return None
