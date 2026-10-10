"""
Empresas (punto 4.1 y 10 del documento de arquitectura).

Una empresa puede representar un cliente, un posible cliente, una
organización o una cuenta comercial. Tiene muchos Contactos y puede
tener muchas Oportunidades.
"""
from django.conf import settings
from django.db import models

from core.models import TenantScopedModel, TimeStampedModel


class Company(TenantScopedModel, TimeStampedModel):
    """Empresa / cuenta comercial."""

    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_companies",
        help_text="Usuario responsable de esta cuenta comercial.",
    )

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ["name"]

    def __str__(self):
        return self.name
