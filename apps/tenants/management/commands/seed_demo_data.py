"""
Carga datos de ejemplo (empresas, contactos, leads, oportunidades,
tareas y notas) en un cliente, para mostrar el CRM en demos.

Uso:
    python manage.py seed_demo_data --tenant demo
"""
import random
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.activities.models import Note, Task
from apps.companies.models import Company
from apps.contacts.models import Contact
from apps.leads.models import Lead
from apps.opportunities.models import Opportunity, PipelineStage
from apps.tenants.models import Tenant
from apps.users.models import User

COMPANIES = [
    ("Agroganadera del Sur S.A.", "Encarnación", "agrosur.com.py"),
    ("Farmacias Centro", "Asunción", "farmaciascentro.com.py"),
    ("Constructora Itapúa", "Encarnación", "constructoraitapua.com.py"),
    ("Logística Chaco", "Filadelfia", "logisticachaco.com.py"),
    ("Clínica San Roque", "Asunción", "clinicasanroque.com.py"),
    ("Distribuidora Guaraní", "Ciudad del Este", "guarani.com.py"),
    ("Colegio Los Pinos", "Luque", "lospinos.edu.py"),
    ("Hotel Costanera", "Asunción", "hotelcostanera.com.py"),
]
PEOPLE = [
    ("María", "Benítez", "Gerente general"), ("Carlos", "Giménez", "Jefe de compras"),
    ("Lucía", "Ortiz", "Administración"), ("Diego", "Ramírez", "Director"),
    ("Sofía", "Acosta", "Contadora"), ("Jorge", "Villalba", "TI"),
    ("Ana", "Duarte", "Directora"), ("Pablo", "Martínez", "Gerente comercial"),
    ("Laura", "Cáceres", "Recepción"), ("Hugo", "Rojas", "Socio"),
]
DEALS = [
    "Implementación Odoo", "Facturación electrónica SIFEN", "Integración Zoho CRM",
    "CRM a medida", "Soporte anual", "Migración de datos", "Portal de clientes",
    "Automatización WhatsApp",
]
LEADS = [
    ("Consulta facturación electrónica", "Roberto Insfrán", "Ferretería El Clavo", "FORMULARIO"),
    ("Quiere un CRM para su equipo", "Natalia Vera", "Inmobiliaria Norte", "REDES_SOCIALES"),
    ("Pidió demo de Odoo", "Fernando Ayala", "Taller Ayala", "LLAMADA"),
    ("Recomendado por Clínica San Roque", "Patricia López", "Odontología Sonrisa", "RECOMENDACION"),
    ("Integración con su e-commerce", "Gustavo Sanabria", "TiendaPy", "CAMPANA_MARKETING"),
    ("Sistema de turnos", "Cecilia Núñez", "Peluquería Glam", "FORMULARIO"),
    ("Cotización soporte", "Marcelo Franco", "Estudio Franco & Asoc.", "REGISTRO_MANUAL"),
    ("Escribió por WhatsApp", "Romina Galeano", "", "REDES_SOCIALES"),
]
STATUSES = ["NUEVO", "NUEVO", "CONTACTADO", "CALIFICADO", "CONTACTADO", "NUEVO", "DESCARTADO", "NUEVO"]


class Command(BaseCommand):
    help = "Carga datos de ejemplo en un cliente (para demos)."

    def add_arguments(self, parser):
        parser.add_argument("--tenant", required=True, help="Slug del cliente.")

    @transaction.atomic
    def handle(self, *args, **options):
        tenant = Tenant.objects.filter(slug=options["tenant"]).first()
        if tenant is None:
            raise CommandError(f"No existe el cliente '{options['tenant']}'.")
        if Company.objects.filter(tenant=tenant).exists():
            raise CommandError("Ese cliente ya tiene datos; no se cargó nada.")
        rng = random.Random(42)
        owner = User.objects.filter(tenant=tenant).order_by("id").first()
        stages = list(PipelineStage.objects.filter(tenant=tenant).order_by("sequence"))
        today = timezone.localdate()

        companies, contacts = [], []
        for i, (name, city, domain) in enumerate(COMPANIES):
            company = Company.objects.create(
                tenant=tenant, name=name, city=city, country="Paraguay",
                email=f"info@{domain}", phone=f"+595 21 {600000 + i * 1371}",
                website=f"https://{domain}", owner=owner,
            )
            companies.append(company)
            for first, last, position in rng.sample(PEOPLE, 2):
                contacts.append(Contact.objects.create(
                    tenant=tenant, first_name=first, last_name=last, position=position,
                    email=f"{first.lower()}.{last.lower()}@{domain}".replace("í", "i").replace("á", "a").replace("é", "e"),
                    phone=f"+595 98{rng.randint(1, 9)} {rng.randint(100000, 999999)}",
                    company=company, owner=owner,
                ))

        for i, company in enumerate(companies):
            stage = stages[i % len(stages)]
            contact = next(c for c in contacts if c.company_id == company.id)
            opp = Opportunity.objects.create(
                tenant=tenant, name=f"{DEALS[i]} - {company.name.split()[0]}", company=company,
                contact=contact, amount=rng.choice([4500000, 8000000, 12500000, 25000000, 38000000, 60000000]),
                probability=stage.probability, stage=stage, assigned_to=owner,
                expected_closing_date=today + timedelta(days=rng.randint(-10, 45)),
                description="Oportunidad de ejemplo para demos.",
            )
            Note.objects.create(tenant=tenant, related_type="opportunity", related_id=opp.id, author=owner,
                                body="Primera reunión hecha. Les interesa avanzar este mes.")

        for (title, name, company, source), status in zip(LEADS, STATUSES):
            lead = Lead.objects.create(
                tenant=tenant, title=title, name=name, company=company, source=source, status=status,
                email=f"{name.split()[0].lower()}@example.com", phone=f"+595 99{rng.randint(1, 9)} {rng.randint(100000, 999999)}",
                assigned_to=owner,
            )
            if status == "NUEVO":
                Task.objects.create(tenant=tenant, title=f"Llamar a {name}", related_type="lead", related_id=lead.id,
                                    due_date=today + timedelta(days=rng.randint(-2, 5)), assigned_to=owner,
                                    priority=rng.choice(["NORMAL", "ALTA"]))

        self.stdout.write(self.style.SUCCESS(f"Datos de ejemplo cargados en '{tenant.slug}'."))
