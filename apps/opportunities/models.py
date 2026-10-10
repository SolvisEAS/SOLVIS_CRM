"""
Oportunidades y etapas del pipeline (puntos 4.4, 9 y 10 del documento).

PipelineStage NO está hardcodeado en el sistema (tal como pide el
punto 9): es un modelo propio para que las etapas comerciales puedan
configurarse sin tocar código.
"""
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.companies.models import Company
from apps.contacts.models import Contact
from core.models import TenantScopedModel, TimeStampedModel


class PipelineStage(TenantScopedModel):
    """Etapa configurable del pipeline comercial (ej: Nueva, Ganada)."""

    name = models.CharField(max_length=100)
    sequence = models.PositiveIntegerField(
        default=0, help_text="Orden de la etapa dentro del pipeline."
    )
    probability = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Probabilidad de cierre asociada a esta etapa (0-100).",
    )
    color = models.CharField(max_length=20, blank=True)
    is_won = models.BooleanField(default=False)
    is_lost = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Etapa del pipeline"
        verbose_name_plural = "Etapas del pipeline"
        ordering = ["sequence"]

    def __str__(self):
        return self.name


class Opportunity(TenantScopedModel, TimeStampedModel):
    """Posible negocio o venta (punto 4.4 del documento)."""

    name = models.CharField(max_length=255)
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="opportunities"
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opportunities",
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    probability = models.PositiveIntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    expected_closing_date = models.DateField(null=True, blank=True)
    stage = models.ForeignKey(
        PipelineStage, on_delete=models.PROTECT, related_name="opportunities"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_opportunities",
    )
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Oportunidad"
        verbose_name_plural = "Oportunidades"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
