"""
Contactos (punto 4.2 y 10 del documento de arquitectura).

Persona relacionada con una Empresa. Puede participar en
Oportunidades comerciales.
"""
from django.conf import settings
from django.db import models

from apps.companies.models import Company
from core.models import TenantScopedModel, TimeStampedModel


class Contact(TenantScopedModel, TimeStampedModel):
    """Persona de contacto dentro de una empresa."""

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    position = models.CharField(max_length=100, blank=True)

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="contacts",
        null=True,
        blank=True,
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_contacts",
    )

    class Meta:
        verbose_name = "Contacto"
        verbose_name_plural = "Contactos"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
