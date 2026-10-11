"""
Pruebas de la API: aislamiento entre clientes, conversión de leads,
historial, permisos y Panel Solvis.

    python manage.py test tests --settings=config.settings.test
"""
from rest_framework.test import APITestCase

from apps.activities.models import TimelineEvent
from apps.companies.models import Company
from apps.leads.models import Lead
from apps.opportunities.models import Opportunity, PipelineStage
from apps.tenants.models import Tenant
from apps.users.models import User


class BaseCase(APITestCase):
    def setUp(self):
        self.acme = Tenant.objects.create(name="Acme", slug="acme")
        self.otro = Tenant.objects.create(name="Otro", slug="otro")
        self.admin = self.make_user("admin_acme", self.acme, "ADMINISTRADOR")
        self.vendedor = self.make_user("vende_acme", self.acme, "VENDEDOR")
        self.ajeno = self.make_user("admin_otro", self.otro, "ADMINISTRADOR")

    def make_user(self, username, tenant, role, **extra):
        user = User(username=username, tenant=tenant, role=role, **extra)
        user.set_password("Clave-segura-123")
        user.save()
        return user

    def login(self, user):
        res = self.client.post("/api/auth/login/", {"username": user.username, "password": "Clave-segura-123"})
        self.assertEqual(res.status_code, 200, res.content)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        return res.data


class TenancyTests(BaseCase):
    def test_new_tenant_gets_default_stages(self):
        self.assertEqual(PipelineStage.objects.filter(tenant=self.acme).count(), 6)

    def test_login_returns_frontend(self):
        data = self.login(self.admin)
        self.assertEqual(data["user"]["tenant"]["frontend"], "solvis")

    def test_records_are_isolated(self):
        Company.objects.create(tenant=self.otro, name="Secreta")
        self.login(self.admin)
        self.client.post("/api/companies/", {"name": "Propia"})
        names = [c["name"] for c in self.client.get("/api/companies/").data["results"]]
        self.assertEqual(names, ["Propia"])
        self.assertEqual(Company.objects.get(name="Propia").tenant, self.acme)

    def test_cannot_link_other_tenant_records(self):
        ajena = Company.objects.create(tenant=self.otro, name="Ajena")
        self.login(self.admin)
        res = self.client.post("/api/contacts/", {"first_name": "A", "last_name": "B", "company": ajena.id})
        self.assertEqual(res.status_code, 400)

    def test_suspended_tenant_is_locked_out(self):
        self.login(self.admin)
        self.acme.is_active = False
        self.acme.save()
        self.assertEqual(self.client.get("/api/users/me/").status_code, 401)
        self.client.credentials()
        res = self.client.post("/api/auth/login/", {"username": "admin_acme", "password": "Clave-segura-123"})
        self.assertEqual(res.status_code, 401)


class CrmFlowTests(BaseCase):
    def test_convert_lead_and_timeline(self):
        self.login(self.vendedor)
        lead_id = self.client.post("/api/leads/", {"title": "Quiere CRM", "name": "Ana Pérez", "company": "Ferretería"}).data["id"]
        res = self.client.post(f"/api/leads/{lead_id}/convert/", {"amount": "1500000"})
        self.assertEqual(res.status_code, 200, res.content)
        opp = Opportunity.objects.get(pk=res.data["opportunity"])
        self.assertEqual(opp.company.name, "Ferretería")
        self.assertEqual(opp.contact.first_name, "Ana")
        self.assertEqual(Lead.objects.get(pk=lead_id).status, "CONVERTIDO")
        again = self.client.post(f"/api/leads/{lead_id}/convert/", {})
        self.assertEqual(again.status_code, 400)
        verbs = list(TimelineEvent.objects.filter(related_type="lead", related_id=lead_id).values_list("verb", flat=True))
        self.assertIn("converted", verbs)
        self.assertIn("created", verbs)

    def test_stage_change_sets_closed_at_and_logs(self):
        self.login(self.admin)
        company = self.client.post("/api/companies/", {"name": "Cliente"}).data["id"]
        stages = {s.name: s.id for s in PipelineStage.objects.filter(tenant=self.acme)}
        opp = self.client.post("/api/opportunities/", {"name": "Venta", "company": company, "stage": stages["Nueva"], "amount": "100"}).data
        self.assertIsNone(opp["closed_at"])
        res = self.client.patch(f"/api/opportunities/{opp['id']}/", {"stage": stages["Ganada"]})
        self.assertIsNotNone(res.data["closed_at"])
        event = TimelineEvent.objects.filter(related_type="opportunity", related_id=opp["id"], verb="updated").first()
        self.assertIn("Etapa: Nueva → Ganada", event.description)
        dash = self.client.get("/api/dashboard/").data
        self.assertEqual(dash["totals"]["won_month_count"], 1)

    def test_deleting_stage_in_use_gives_clear_error(self):
        self.login(self.admin)
        company = Company.objects.create(tenant=self.acme, name="C")
        stage = PipelineStage.objects.filter(tenant=self.acme).first()
        Opportunity.objects.create(tenant=self.acme, name="O", company=company, stage=stage)
        res = self.client.delete(f"/api/pipeline-stages/{stage.id}/")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "protected")

    def test_seller_cannot_edit_stages(self):
        self.login(self.vendedor)
        stage = PipelineStage.objects.filter(tenant=self.acme).first()
        self.assertEqual(self.client.patch(f"/api/pipeline-stages/{stage.id}/", {"name": "X"}).status_code, 403)


class UserManagementTests(BaseCase):
    def test_change_own_password(self):
        self.login(self.vendedor)
        bad = self.client.post("/api/users/me/password/", {"current_password": "mal", "new_password": "Otra-clave-456"})
        self.assertEqual(bad.status_code, 400)
        ok = self.client.post("/api/users/me/password/", {"current_password": "Clave-segura-123", "new_password": "Otra-clave-456"})
        self.assertEqual(ok.status_code, 200)
        self.vendedor.refresh_from_db()
        self.assertTrue(self.vendedor.check_password("Otra-clave-456"))

    def test_tenant_admin_manages_only_own_users(self):
        self.login(self.admin)
        res = self.client.post(f"/api/users/{self.vendedor.id}/set-password/", {})
        self.assertEqual(res.status_code, 200)
        self.assertRegex(res.data["generated_password"], r"^\w{4}-\w{4}-\w{4}-\w{4}$")
        self.assertEqual(self.client.post(f"/api/users/{self.ajeno.id}/set-password/", {}).status_code, 404)
        self.assertEqual(self.client.patch(f"/api/users/{self.admin.id}/", {"is_active": False}).status_code, 400)

    def test_seller_cannot_manage_users(self):
        self.login(self.vendedor)
        self.assertEqual(self.client.post(f"/api/users/{self.admin.id}/set-password/", {}).status_code, 403)


class BackofficeTests(BaseCase):
    def test_only_staff(self):
        self.login(self.admin)
        self.assertEqual(self.client.get("/api/backoffice/tenants/").status_code, 403)

    def test_staff_creates_tenant_and_user(self):
        staff = self.make_user("solvis", self.otro, "ADMINISTRADOR", is_staff=True)
        self.login(staff)
        tenant = self.client.post("/api/backoffice/tenants/", {"name": "Nuevo", "slug": "nuevo", "frontend": "solvis"}).data
        res = self.client.post(f"/api/backoffice/tenants/{tenant['id']}/users/", {"username": "nuevo1", "role": "ADMINISTRADOR"})
        self.assertEqual(res.status_code, 201)
        self.client.credentials()
        login = self.client.post("/api/auth/login/", {"username": "nuevo1", "password": res.data["generated_password"]})
        self.assertEqual(login.status_code, 200)
