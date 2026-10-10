"""
Leads (punto 4.3 y 10 del documento de arquitectura).

Representa un posible cliente o prospecto, antes de convertirse en
Contacto/Empresa/Oportunidad formales. Esa conversión es lógica de
negocio de la Fase 3 — acá solo se modela el Lead en sí.

`company` se guarda como texto libre a propósito: en esta etapa el
prospecto todavía puede no tener una Company real creada en el
sistema. Cuando se implemente la conversión (Fase 3), ahí sí se
vincula a un Company/Contact reales.
"""
from django.conf import settings
from django.db import models

from core.models import TenantScopedModel, TimeStampedModel


class Lead(TenantScopedModel, TimeStampedModel):
    class Source(models.TextChoices):
        FORMULARIO = "FORMULARIO", "Formulario"
        REDES_SOCIALES = "REDES_SOCIALES", "Redes sociales"
        LLAMADA = "LLAMADA", "Llamada"
        RECOMENDACION = "RECOMENDACION", "Recomendación"
        REGISTRO_MANUAL = "REGISTRO_MANUAL", "Registro manual"
        CAMPANA_MARKETING = "CAMPANA_MARKETING", "Campaña de marketing"

    class Status(models.TextChoices):
        NUEVO = "NUEVO", "Nuevo"
        CONTACTADO = "CONTACTADO", "Contactado"
        CALIFICADO = "CALIFICADO", "Calificado"
        DESCARTADO = "DESCARTADO", "Descartado"
        CONVERTIDO = "CONVERTIDO", "Convertido"

    title = models.CharField(max_length=255, help_text="Título/descripción breve del lead.")
    name = models.CharField(max_length=255, help_text="Nombre de la persona de contacto.")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    company = models.CharField(
        max_length=255,
        blank=True,
        help_text="Nombre de la empresa del prospecto (texto libre hasta la conversión).",
    )
    source = models.CharField(max_length=30, choices=Source.choices, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NUEVO
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_leads",
    )
    description = models.TextField(blank=True)

    # Resultado de la conversión (Lead -> Empresa + Contacto + Oportunidad).
    converted_at = models.DateTimeField(null=True, blank=True, editable=False)
    converted_company = models.ForeignKey(
        "companies.Company", on_delete=models.SET_NULL, null=True, blank=True,
        editable=False, related_name="+",
    )
    converted_contact = models.ForeignKey(
        "contacts.Contact", on_delete=models.SET_NULL, null=True, blank=True,
        editable=False, related_name="+",
    )
    converted_opportunity = models.ForeignKey(
        "opportunities.Opportunity", on_delete=models.SET_NULL, null=True, blank=True,
        editable=False, related_name="+",
    )

    class Meta:
        verbose_name = "Lead"
        verbose_name_plural = "Leads"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.name})"
