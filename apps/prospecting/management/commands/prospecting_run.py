from django.core.management.base import BaseCommand

from apps.prospecting.runner import execute_run


class Command(BaseCommand):
    help = "Ejecuta una búsqueda de la Captación (la lanza la API en un proceso aparte)."

    def add_arguments(self, parser):
        parser.add_argument("run_id", type=int)

    def handle(self, *args, run_id, **options):
        run = execute_run(run_id)
        self.stdout.write(f"{run.get_status_display()}: {run.new_count} prospectos nuevos, US$ {run.cost_usd}")
