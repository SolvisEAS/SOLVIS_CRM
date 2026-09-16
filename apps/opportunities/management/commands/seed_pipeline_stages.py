"""
Siembra las etapas por defecto del pipeline comercial (punto 9 del
documento). Se implementa como management command en lugar de una
migración de datos, para no atarlo al nombre de una migración de
esquema que todavía no existe (se genera con makemigrations en cada
entorno).

Uso:
    python manage.py seed_pipeline_stages
"""
from django.core.management.base import BaseCommand

from apps.opportunities.models import PipelineStage

DEFAULT_STAGES = [
    {"name": "Nueva", "sequence": 1, "probability": 10},
    {"name": "Calificada", "sequence": 2, "probability": 25},
    {"name": "Propuesta", "sequence": 3, "probability": 50},
    {"name": "Negociación", "sequence": 4, "probability": 75},
    {"name": "Ganada", "sequence": 5, "probability": 100, "is_won": True},
    {"name": "Perdida", "sequence": 6, "probability": 0, "is_lost": True},
]


class Command(BaseCommand):
    help = "Crea las etapas de pipeline por defecto (Nueva, Calificada, Propuesta, Negociación, Ganada, Perdida)."

    def handle(self, *args, **options):
        created_count = 0
        for stage_data in DEFAULT_STAGES:
            _, created = PipelineStage.objects.get_or_create(
                name=stage_data["name"], defaults=stage_data
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Listo. {created_count} etapas nuevas creadas "
                f"({len(DEFAULT_STAGES) - created_count} ya existían)."
            )
        )
