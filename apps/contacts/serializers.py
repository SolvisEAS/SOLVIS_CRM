from rest_framework import serializers

from .models import Contact


class ContactSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    owner_username = serializers.CharField(source="owner.username", read_only=True)

    class Meta:
        model = Contact
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "position",
            "company",
            "company_name",
            "owner",
            "owner_username",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
