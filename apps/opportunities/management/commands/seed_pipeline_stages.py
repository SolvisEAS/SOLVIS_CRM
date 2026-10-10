"""
Siembra las etapas por defecto del pipeline comercial (punto 9 del
documento) para un cliente, o para todos si no se indica ninguno.
Los clientes nuevos ya las reciben solas al crearse.

Uso:
    python manage.py seed_pipeline_stages [--tenant <slug>]
"""
from django.core.management.base import BaseCommand, CommandError

from apps.opportunities.stages import DEFAULT_STAGES, seed_default_stages
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = "Crea las etapas de pipeline por defecto (Nueva, Calificada, Propuesta, Negociación, Ganada, Perdida)."

    def add_arguments(self, parser):
        parser.add_argument("--tenant", help="Slug del cliente (por defecto: todos).")

    def handle(self, *args, **options):
        tenants = Tenant.objects.all()
        if options["tenant"]:
            tenants = tenants.filter(slug=options["tenant"])
            if not tenants.exists():
                raise CommandError(f"No existe el cliente '{options['tenant']}'.")
        for tenant in tenants:
            created_count = seed_default_stages(tenant)
            self.stdout.write(
                self.style.SUCCESS(
                    f"{tenant.slug}: {created_count} etapas nuevas creadas "
                    f"({len(DEFAULT_STAGES) - created_count} ya existían)."
                )
            )
