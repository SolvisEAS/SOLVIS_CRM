from rest_framework import serializers

from core.tenancy import TenantScopedSerializerMixin

from .models import Lead


class LeadSerializer(TenantScopedSerializerMixin, serializers.ModelSerializer):
    assigned_to_username = serializers.CharField(
        source="assigned_to.username", read_only=True
    )

    class Meta:
        model = Lead
        fields = (
            "id",
            "title",
            "name",
            "email",
            "phone",
            "company",
            "source",
            "status",
            "assigned_to",
            "assigned_to_username",
            "description",
            "converted_at",
            "converted_company",
            "converted_contact",
            "converted_opportunity",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id", "created_at", "updated_at", "converted_at",
            "converted_company", "converted_contact", "converted_opportunity",
        )
