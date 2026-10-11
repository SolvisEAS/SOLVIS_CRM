"""
Actividades (Fase 3): Notas y Tareas.

Se cuelgan de cualquier registro del CRM (lead, contacto, empresa u
oportunidad) con el par related_type + related_id, igual que las
listas relacionadas "Notas" y "Actividades abiertas" de Zoho CRM.
"""
from django.conf import settings
from django.db import models

from core.models import TenantScopedModel, TimeStampedModel


class RelatedType(models.TextChoices):
    LEAD = "lead", "Lead"
    CONTACT = "contact", "Contacto"
    COMPANY = "company", "Empresa"
    OPPORTUNITY = "opportunity", "Oportunidad"


class Note(TenantScopedModel, TimeStampedModel):
    related_type = models.CharField(max_length=20, choices=RelatedType.choices)
    related_id = models.PositiveBigIntegerField()
    body = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="notes",
    )

    class Meta:
        verbose_name = "Nota"
        verbose_name_plural = "Notas"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant", "related_type", "related_id"])]

    def __str__(self):
        return self.body[:50]


class Task(TenantScopedModel, TimeStampedModel):
    class Status(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_CURSO = "EN_CURSO", "En curso"
        COMPLETADA = "COMPLETADA", "Completada"

    class Priority(models.TextChoices):
        BAJA = "BAJA", "Baja"
        NORMAL = "NORMAL", "Normal"
        ALTA = "ALTA", "Alta"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDIENTE)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    related_type = models.CharField(max_length=20, choices=RelatedType.choices, blank=True)
    related_id = models.PositiveBigIntegerField(null=True, blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_tasks",
    )

    class Meta:
        verbose_name = "Tarea"
        verbose_name_plural = "Tareas"
        ordering = ["status", "due_date", "-created_at"]

    def __str__(self):
        return self.title


class TimelineEvent(TenantScopedModel):
    """Historial de un registro (como el "Timeline" de Zoho): quién hizo qué y cuándo."""

    related_type = models.CharField(max_length=20, choices=RelatedType.choices)
    related_id = models.PositiveBigIntegerField()
    verb = models.CharField(max_length=30)
    description = models.CharField(max_length=500)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Evento del historial"
        verbose_name_plural = "Historial"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["tenant", "related_type", "related_id"])]

    def __str__(self):
        return self.description
