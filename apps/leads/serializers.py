from rest_framework import serializers

from .models import Lead


class LeadSerializer(serializers.ModelSerializer):
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
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
