from rest_framework import serializers

from core.tenancy import TenantScopedSerializerMixin

from .models import Company


class CompanySerializer(TenantScopedSerializerMixin, serializers.ModelSerializer):
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    contacts_count = serializers.IntegerField(read_only=True)
    opportunities_count = serializers.IntegerField(read_only=True)

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
            "contacts_count",
            "opportunities_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
