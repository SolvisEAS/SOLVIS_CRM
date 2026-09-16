"""
Piezas de modelo reutilizables por todas las apps del CRM.

Cada módulo futuro (companies, contacts, leads, opportunities, etc.)
va a heredar de TimeStampedModel en lugar de repetir created_at /
updated_at en cada modelo.
"""
from django.db import models


class TimeStampedModel(models.Model):
    """Agrega created_at / updated_at automáticos a cualquier modelo."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
