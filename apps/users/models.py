"""
Modelo de usuario personalizado (punto 10 del documento de arquitectura).

Se hereda de AbstractUser en lugar de crear un modelo desde cero:
esto mantiene gratis todo lo que Django ya resuelve bien (contraseñas
hasheadas, permisos, grupos, integración con el admin) y solo agrega
lo que el CRM necesita de más: el campo `role`.

Definir esto en la Fase 1, ANTES de la primera migración, es
intencional: cambiar AUTH_USER_MODEL después de migrar es costoso.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Usuario del sistema, con rol dentro del CRM."""

    class Roles(models.TextChoices):
        ADMINISTRADOR = "ADMINISTRADOR", "Administrador"
        GERENTE = "GERENTE", "Gerente"
        VENDEDOR = "VENDEDOR", "Vendedor"
        USUARIO = "USUARIO", "Usuario"

    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.USUARIO,
        help_text="Rol del usuario dentro del CRM (punto 12 del documento).",
    )
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
        help_text="Cliente al que pertenece. Define qué datos ve y qué front abre.",
    )

    def __str__(self):
        return self.get_full_name() or self.username
