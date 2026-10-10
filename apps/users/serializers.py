from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.tenants.serializers import TenantSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Representación de un usuario para lectura (ej: endpoint /me/)."""

    full_name = serializers.SerializerMethodField()
    tenant = TenantSerializer(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "tenant",
            "is_staff",
            "is_active",
            "date_joined",
        )
        read_only_fields = ("id", "is_active", "is_staff", "date_joined", "tenant")

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class UserListSerializer(serializers.ModelSerializer):
    """Versión liviana para listas y selectores ("Asignado a")."""

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "full_name", "role", "is_active")
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Alta de un usuario dentro del cliente de quien lo crea, con contraseña hasheada."""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "password",
        )
        read_only_fields = ("id",)

    def create(self, validated_data):
        # set_password aplica el hashing configurado por Django.
        # Nunca se guarda la contraseña en texto plano (punto 15 del doc).
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class TenantTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Login: además de los tokens devuelve el usuario y su cliente, para
    que el front sepa qué front abrir (tenant.frontend).
    """

    default_error_messages = {
        **TokenObtainPairSerializer.default_error_messages,
        "inactive_tenant": "El acceso de esta empresa está suspendido.",
    }

    def validate(self, attrs):
        data = super().validate(attrs)
        tenant = self.user.tenant
        if tenant is not None and not tenant.is_active:
            from rest_framework_simplejwt.exceptions import AuthenticationFailed

            raise AuthenticationFailed(self.error_messages["inactive_tenant"], "inactive_tenant")
        data["user"] = UserSerializer(self.user).data
        return data
