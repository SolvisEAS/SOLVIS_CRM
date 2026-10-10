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


class TenantSettingsSerializer(serializers.ModelSerializer):
    """Lo que el administrador de un cliente puede ver y editar de su empresa."""

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
            "created_at",
        )
        read_only_fields = ("id", "slug", "frontend", "created_at")

    def validate_primary_color(self, value):
        return self._color(value)

    def validate_accent_color(self, value):
        return self._color(value)

    @staticmethod
    def _color(value):
        import re

        if value and not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            raise serializers.ValidationError("Usá un color en formato #RRGGBB.")
        return value
