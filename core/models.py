"""
Piezas de modelo reutilizables por todas las apps del CRM.

Cada módulo (companies, contacts, leads, opportunities, etc.) hereda
de TimeStampedModel en lugar de repetir created_at / updated_at, y de
TenantScopedModel para quedar atado a un cliente (ver apps.tenants).
"""
from django.db import models


class TimeStampedModel(models.Model):
    """Agrega created_at / updated_at automáticos a cualquier modelo."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantScopedModel(models.Model):
    """Registro que pertenece a un cliente. El tenant lo pone la API, nunca el usuario."""

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        editable=False,
        related_name="+",
    )

    class Meta:
        abstract = True
