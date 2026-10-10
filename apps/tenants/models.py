"""
Clientes del CRM (multi-tenant).

SOLVIS CRM es un back general que se vende a varios clientes. Cada
cliente es un Tenant: sus usuarios solo ven los datos de su propio
Tenant, y al iniciar sesión se abre el front indicado en `frontend`
(una carpeta dentro de /frontends). Solvis es el primer Tenant y usa
el front general "solvis", que también sirve para las demos.
"""
from django.core.validators import RegexValidator
from django.db import models

slug_validator = RegexValidator(
    r"^[a-z0-9][a-z0-9-]*$", "Solo minúsculas, números y guiones."
)


class Tenant(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=60, unique=True)
    frontend = models.CharField(
        max_length=60,
        default="solvis",
        validators=[slug_validator],
        help_text="Carpeta del front que abre este cliente (frontends/<frontend>/).",
    )
    primary_color = models.CharField(max_length=20, blank=True)
    accent_color = models.CharField(max_length=20, blank=True)
    logo_url = models.CharField(max_length=255, blank=True)
    currency = models.CharField(max_length=10, default="PYG")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["name"]

    def __str__(self):
        return self.name
