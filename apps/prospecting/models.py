"""
Captación (solo personal de Solvis): búsqueda de posibles clientes en
publicaciones públicas de internet.

- Search: qué buscar (palabras, países, período) para encontrar gente que
  pide un CRM, un sistema o un desarrollador.
- SearchRun: cada vez que Claude sale a buscar, con lo que encontró y cuánto costó.
- Prospect: una persona o empresa encontrada, de dónde salió y cómo contactarla.
  Después de contactarla se convierte en Contacto + Oportunidad (vía un Lead).
- ProspectingSettings: clave de la API de Anthropic, modelo y tope de gasto.
"""
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.db import models

from core.models import TenantScopedModel, TimeStampedModel

TRACKING_PARAMS = {"fbclid", "gclid", "igshid", "mibextid", "ref", "si"}


def normalize_url(url):
    """Misma publicación = misma clave, aunque cambien www, parámetros de rastreo o la barra final."""
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return url.strip().lower()[:500]
    host = parts.netloc.lower().removeprefix("www.").removeprefix("m.").removeprefix("old.")
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query)
                       if not k.lower().startswith("utm_") and k.lower() not in TRACKING_PARAMS])
    return urlunsplit(("https", host, parts.path.rstrip("/"), query, ""))[:500]


class ProspectingSettings(TenantScopedModel):
    class Model(models.TextChoices):
        OPUS = "claude-opus-5-5", "Claude Opus 5.5 (mejor calidad)"
        SONNET = "claude-sonnet-5-5", "Claude Sonnet 5.5 (más económico)"

    # Nunca se devuelve por la API: solo se muestran los últimos 4 caracteres.
    anthropic_api_key = models.CharField(max_length=255, blank=True)
    model = models.CharField(max_length=40, choices=Model.choices, default=Model.OPUS)
    monthly_budget_usd = models.DecimalField(
        max_digits=8, decimal_places=2, default=20,
        help_text="Tope de gasto estimado por mes. Al llegar, no se lanzan más búsquedas.",
    )

    class Meta:
        verbose_name = "Configuración de captación"
        verbose_name_plural = "Configuración de captación"
        constraints = [models.UniqueConstraint(fields=["tenant"], name="prospecting_settings_one_per_tenant")]


class Search(TenantScopedModel, TimeStampedModel):
    class Depth(models.TextChoices):
        RAPIDA = "RAPIDA", "Rápida"
        NORMAL = "NORMAL", "Normal"
        PROFUNDA = "PROFUNDA", "Profunda"

    name = models.CharField(max_length=150)
    keywords = models.TextField(help_text="Frases a buscar, una por línea (ej: busco un CRM).")
    offering = models.TextField(
        blank=True, default="CRM y desarrollo de software a medida (sistemas, páginas web, apps)",
        help_text="Qué vende Solvis: sirve para decidir quién es un buen prospecto.",
    )
    countries = models.CharField(max_length=200, default="Paraguay", help_text="Países, separados por coma.")
    period_days = models.PositiveIntegerField(default=30, help_text="Solo publicaciones de los últimos N días.")
    depth = models.CharField(max_length=10, choices=Depth.choices, default=Depth.NORMAL)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )

    class Meta:
        verbose_name = "Búsqueda"
        verbose_name_plural = "Búsquedas"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def keyword_list(self):
        return [k.strip() for k in self.keywords.splitlines() if k.strip()]


class SearchRun(TenantScopedModel):
    class Status(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_CURSO = "EN_CURSO", "Buscando"
        TERMINADA = "TERMINADA", "Terminada"
        ERROR = "ERROR", "Con error"

    search = models.ForeignKey(Search, on_delete=models.CASCADE, related_name="runs")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDIENTE)
    model = models.CharField(max_length=40, blank=True)
    worker_pid = models.PositiveIntegerField(null=True, blank=True, editable=False,
                                             help_text="Proceso que ejecuta la búsqueda (para detectar si se cortó).")
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    found_count = models.PositiveIntegerField(default=0, help_text="Resultados que trajo Claude.")
    new_count = models.PositiveIntegerField(default=0, help_text="Prospectos nuevos guardados.")
    duplicate_count = models.PositiveIntegerField(default=0)
    out_of_range_count = models.PositiveIntegerField(default=0)
    web_searches = models.PositiveIntegerField(default=0)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    summary = models.TextField(blank=True)
    error = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )

    class Meta:
        verbose_name = "Ejecución de búsqueda"
        verbose_name_plural = "Ejecuciones de búsqueda"
        ordering = ["-created_at"]


class Prospect(TenantScopedModel, TimeStampedModel):
    class Status(models.TextChoices):
        NUEVO = "NUEVO", "Nuevo"
        CONTACTADO = "CONTACTADO", "Contactado"
        RESPONDIO = "RESPONDIO", "Respondió"
        DESCARTADO = "DESCARTADO", "Descartado"
        CONVERTIDO = "CONVERTIDO", "Convertido"

    search = models.ForeignKey(Search, on_delete=models.SET_NULL, null=True, blank=True, related_name="prospects")
    run = models.ForeignKey(SearchRun, on_delete=models.SET_NULL, null=True, blank=True, related_name="prospects")

    name = models.CharField(max_length=200, blank=True, help_text="Persona o cuenta que publicó.")
    company = models.CharField(max_length=200, blank=True)
    need = models.CharField(max_length=500, help_text="Qué necesita, en una frase.")
    quote = models.TextField(blank=True, help_text="Lo que dijo (extracto de la publicación).")

    # De dónde viene.
    source_url = models.URLField(max_length=1000, blank=True)
    source_key = models.CharField(max_length=500, blank=True, editable=False, db_index=True,
                                  help_text="URL normalizada, para no guardar dos veces la misma publicación.")
    source_name = models.CharField(max_length=100, blank=True, help_text="Ej: Reddit, Facebook, foro, Workana.")
    published_at = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=150, blank=True)

    # Cómo contactarla: solo lo que la persona dejó publicado.
    email = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=60, blank=True)
    whatsapp = models.CharField(max_length=60, blank=True)
    instagram = models.CharField(max_length=200, blank=True)
    facebook = models.CharField(max_length=300, blank=True)
    linkedin = models.CharField(max_length=300, blank=True)
    twitter = models.CharField(max_length=200, blank=True)
    website = models.CharField(max_length=300, blank=True)
    other_contact = models.CharField(max_length=300, blank=True)

    score = models.PositiveSmallIntegerField(default=50, help_text="Interés estimado de 0 a 100.")
    score_reason = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NUEVO)
    notes = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    contacted_at = models.DateTimeField(null=True, blank=True)
    lead = models.ForeignKey("leads.Lead", on_delete=models.SET_NULL, null=True, blank=True,
                             editable=False, related_name="+")

    class Meta:
        verbose_name = "Prospecto"
        verbose_name_plural = "Prospectos"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name or self.need[:60]

    CONTACT_FIELDS = ("email", "phone", "whatsapp", "instagram", "facebook", "linkedin", "twitter",
                      "website", "other_contact")

    def save(self, *args, **kwargs):
        self.source_key = normalize_url(self.source_url) if self.source_url else ""
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"source_key"}
        super().save(*args, **kwargs)

    @property
    def has_contact(self):
        return any(getattr(self, f) for f in self.CONTACT_FIELDS)
