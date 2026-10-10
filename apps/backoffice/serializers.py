from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.tenants.models import Tenant

User = get_user_model()


class BackofficeTenantSerializer(serializers.ModelSerializer):
    users_count = serializers.IntegerField(read_only=True)
    active_users = serializers.IntegerField(read_only=True)
    last_login = serializers.DateTimeField(read_only=True)
    companies_count = serializers.IntegerField(read_only=True)
    leads_count = serializers.IntegerField(read_only=True)
    opportunities_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tenant
        fields = (
            "id", "name", "slug", "frontend", "primary_color", "accent_color", "logo_url",
            "currency", "is_active", "created_at",
            "users_count", "active_users", "last_login", "companies_count", "leads_count", "opportunities_count",
        )
        read_only_fields = ("id", "created_at")

    def validate_slug(self, value):
        if self.instance and value != self.instance.slug:
            raise serializers.ValidationError("El identificador no se puede cambiar una vez creado.")
        return value


class BackofficeUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, min_length=8)

    class Meta:
        model = User
        fields = (
            "id", "username", "email", "first_name", "last_name", "full_name", "role",
            "is_active", "is_staff", "last_login", "date_joined", "tenant", "password",
        )
        read_only_fields = ("id", "is_staff", "last_login", "date_joined", "tenant")

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
