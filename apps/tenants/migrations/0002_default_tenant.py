"""
Crea el cliente "Solvis" y le asigna todo lo que existía antes del
multi-tenant (usuarios, empresas, contactos, leads, oportunidades y
etapas), para que una base de la Fase 2 siga funcionando igual.
"""
from django.db import migrations

DEFAULT_STAGES = [
    {"name": "Nueva", "sequence": 1, "probability": 10, "color": "#64748b"},
    {"name": "Calificada", "sequence": 2, "probability": 25, "color": "#0ea5e9"},
    {"name": "Propuesta", "sequence": 3, "probability": 50, "color": "#7b3fe4"},
    {"name": "Negociación", "sequence": 4, "probability": 75, "color": "#f59e0b"},
    {"name": "Ganada", "sequence": 5, "probability": 100, "is_won": True, "color": "#16a34a"},
    {"name": "Perdida", "sequence": 6, "probability": 0, "is_lost": True, "color": "#dc2626"},
]


def forwards(apps, schema_editor):
    Tenant = apps.get_model("tenants", "Tenant")
    solvis, _ = Tenant.objects.get_or_create(
        slug="solvis",
        defaults={
            "name": "Solvis EAS",
            "frontend": "solvis",
            "primary_color": "#0E2959",
            "accent_color": "#7B3FE4",
            "currency": "PYG",
        },
    )
    for app_label, model_name in [
        ("users", "User"),
        ("companies", "Company"),
        ("contacts", "Contact"),
        ("leads", "Lead"),
        ("opportunities", "Opportunity"),
        ("opportunities", "PipelineStage"),
    ]:
        apps.get_model(app_label, model_name).objects.filter(tenant__isnull=True).update(tenant=solvis)

    PipelineStage = apps.get_model("opportunities", "PipelineStage")
    if not PipelineStage.objects.filter(tenant=solvis).exists():
        for data in DEFAULT_STAGES:
            PipelineStage.objects.create(tenant=solvis, **data)


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0001_initial"),
        ("users", "0002_user_tenant"),
        ("companies", "0002_company_tenant"),
        ("contacts", "0002_contact_tenant"),
        ("leads", "0002_lead_converted_at_lead_converted_company_and_more"),
        ("opportunities", "0002_opportunity_tenant_pipelinestage_tenant"),
    ]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
