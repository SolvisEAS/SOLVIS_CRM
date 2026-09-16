from rest_framework import serializers

from .models import Company


class CompanySerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source="owner.username", read_only=True)

    class Meta:
        model = Company
        fields = (
            "id",
            "name",
            "email",
            "phone",
            "website",
            "address",
            "city",
            "country",
            "owner",
            "owner_username",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
