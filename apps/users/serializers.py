from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Representación de un usuario para lectura (ej: endpoint /me/)."""

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "date_joined",
        )
        read_only_fields = ("id", "is_active", "date_joined")


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Registro de un nuevo usuario, con contraseña hasheada correctamente."""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
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
