"""Etapas por defecto del pipeline (punto 9 del documento), por cliente."""
from .models import PipelineStage

DEFAULT_STAGES = [
    {"name": "Nueva", "sequence": 1, "probability": 10, "color": "#64748b"},
    {"name": "Calificada", "sequence": 2, "probability": 25, "color": "#0ea5e9"},
    {"name": "Propuesta", "sequence": 3, "probability": 50, "color": "#7b3fe4"},
    {"name": "Negociación", "sequence": 4, "probability": 75, "color": "#f59e0b"},
    {"name": "Ganada", "sequence": 5, "probability": 100, "is_won": True, "color": "#16a34a"},
    {"name": "Perdida", "sequence": 6, "probability": 0, "is_lost": True, "color": "#dc2626"},
]


def seed_default_stages(tenant):
    """Crea las etapas que falten para `tenant`. Devuelve cuántas creó."""
    created_count = 0
    for stage_data in DEFAULT_STAGES:
        data = dict(stage_data)
        _, created = PipelineStage.objects.get_or_create(
            tenant=tenant, name=data.pop("name"), defaults=data
        )
        created_count += int(created)
    return created_count
