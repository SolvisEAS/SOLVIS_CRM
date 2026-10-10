from rest_framework import serializers

from .models import Tenant


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = (
            "id",
            "name",
            "slug",
            "frontend",
            "primary_color",
            "accent_color",
            "logo_url",
            "currency",
        )
        read_only_fields = fields
