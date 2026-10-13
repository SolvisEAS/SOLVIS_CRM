"""
Pruebas de la Captación: permisos, búsquedas con Claude (simulado),
deduplicación, costo y conversión a Contacto + Oportunidad.

    python manage.py test tests --settings=config.settings.test
"""
import json
from datetime import timedelta
from types import SimpleNamespace
from unittest import mock

from django.utils import timezone

from apps.contacts.models import Contact
from apps.leads.models import Lead
from apps.opportunities.models import Opportunity
from apps.prospecting.models import Prospect, ProspectingSettings, Search, SearchRun
from apps.prospecting.runner import execute_run, normalize_url

from .test_api import BaseCase


def usage(inp=1000, out=500, searches=0):
    return SimpleNamespace(input_tokens=inp, output_tokens=out, cache_read_input_tokens=0,
                           cache_creation_input_tokens=0, server_tool_use=SimpleNamespace(web_search_requests=searches))


def message(text, stop="end_turn", **kw):
    return SimpleNamespace(stop_reason=stop, stop_details=None, content=[SimpleNamespace(type="text", text=text)],
                           usage=usage(**kw))


class FakeStream:
    def __init__(self, response):
        self.response = response

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self.response


class FakeClient:
    """Imita client.beta.messages: stream() para investigar y create() para extraer."""

    def __init__(self, research, extracted):
        self.research = list(research)
        self.extracted = extracted
        self.stream_calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self.stream, create=self.create))

    def stream(self, **kwargs):
        self.stream_calls.append(kwargs)
        return FakeStream(self.research.pop(0))

    def create(self, **kwargs):
        return message(json.dumps(self.extracted), inp=2000, out=800)


def item(**kw):
    base = {f: "" for f in ("name", "company", "need", "quote", "source_url", "source_name", "published_at",
                            "location", "email", "phone", "whatsapp", "instagram", "facebook", "linkedin",
                            "twitter", "website", "other_contact", "score_reason")}
    base["score"] = 70
    base.update(kw)
    return base


class ProspectingCase(BaseCase):
    def setUp(self):
        super().setUp()
        self.staff = self.make_user("solvis_staff", self.acme, "ADMINISTRADOR", is_staff=True)
        self.search = Search.objects.create(tenant=self.acme, name="CRM Paraguay", keywords="busco un CRM",
                                            period_days=30)

    def set_key(self, tenant=None):
        ProspectingSettings.objects.update_or_create(tenant=tenant or self.acme,
                                                     defaults={"anthropic_api_key": "sk-ant-prueba-1234"})


class PermissionTests(ProspectingCase):
    def test_only_staff(self):
        self.login(self.admin)
        self.assertEqual(self.client.get("/api/prospecting/prospects/").status_code, 403)
        self.assertEqual(self.client.get("/api/prospecting/settings/").status_code, 403)

    def test_staff_only_sees_own_tenant(self):
        Prospect.objects.create(tenant=self.otro, need="Ajeno")
        Prospect.objects.create(tenant=self.acme, need="Propio")
        self.login(self.staff)
        needs = [p["need"] for p in self.client.get("/api/prospecting/prospects/").data["results"]]
        self.assertEqual(needs, ["Propio"])

    def test_api_key_is_never_returned(self):
        self.login(self.staff)
        res = self.client.put("/api/prospecting/settings/", {"api_key": "sk-ant-secreta-9876"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["has_api_key"])
        self.assertEqual(res.data["api_key_hint"], "…9876")
        self.assertNotIn("sk-ant-secreta-9876", json.dumps(self.client.get("/api/prospecting/settings/").data))


class RunTests(ProspectingCase):
    def test_run_needs_api_key(self):
        self.login(self.staff)
        res = self.client.post(f"/api/prospecting/searches/{self.search.id}/run/")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "missing_api_key")

    @mock.patch("apps.prospecting.runner.launch")
    def test_one_run_at_a_time(self, launch):
        self.set_key()
        self.login(self.staff)
        res = self.client.post(f"/api/prospecting/searches/{self.search.id}/run/")
        self.assertEqual(res.status_code, 202)
        launch.assert_called_once()
        res = self.client.post(f"/api/prospecting/searches/{self.search.id}/run/")
        self.assertEqual(res.data["code"], "run_in_progress")

    @mock.patch("apps.prospecting.runner.launch")
    def test_budget_limit(self, launch):
        self.set_key()
        SearchRun.objects.create(tenant=self.acme, search=self.search, status="TERMINADA", cost_usd=25)
        self.login(self.staff)
        res = self.client.post(f"/api/prospecting/searches/{self.search.id}/run/")
        self.assertEqual(res.data["code"], "budget_reached")
        launch.assert_not_called()

    def test_execute_saves_new_prospects(self):
        self.set_key()
        today = timezone.localdate()
        Prospect.objects.create(tenant=self.acme, need="Ya estaba", source_url="https://www.reddit.com/r/py/abc/")
        extracted = {"summary": "Hay demanda en Reddit.", "prospects": [
            item(name="Ana", need="Busca CRM para su ferretería", source_url="https://reddit.com/r/py/nuevo?utm_source=x",
                 source_name="Reddit", published_at=str(today - timedelta(days=3)), instagram="@ana",
                 email="no-es-un-correo", score=140),
            item(need="Repetido", source_url="https://reddit.com/r/py/abc"),
            item(need="Viejo", source_url="https://foro.com/viejo", published_at=str(today - timedelta(days=90))),
        ]}
        client = FakeClient([message("informe parcial", stop="pause_turn", searches=2),
                             message("informe final", searches=3)], extracted)
        run = SearchRun.objects.create(tenant=self.acme, search=self.search, model="claude-opus-5-5")
        run = execute_run(run.id, client=client)

        self.assertEqual(run.status, "TERMINADA", run.error)
        self.assertEqual((run.found_count, run.new_count, run.duplicate_count, run.out_of_range_count), (3, 1, 1, 1))
        self.assertEqual(len(client.stream_calls), 2)  # siguió después de la pausa de la búsqueda web
        self.assertEqual(run.web_searches, 5)
        self.assertGreater(run.cost_usd, 0)
        ana = Prospect.objects.get(name="Ana")
        self.assertEqual((ana.score, ana.email, ana.instagram, ana.search), (100, "", "@ana", self.search))
        self.assertEqual(ana.source_key, normalize_url("https://www.reddit.com/r/py/nuevo"))

    def test_dead_run_is_closed(self):
        run = SearchRun.objects.create(tenant=self.acme, search=self.search, status="EN_CURSO", worker_pid=999999999)
        self.login(self.staff)
        self.client.get("/api/prospecting/runs/")
        run.refresh_from_db()
        self.assertEqual(run.status, "ERROR")

    def test_refusal_is_reported(self):
        refused = SimpleNamespace(stop_reason="refusal", stop_details=SimpleNamespace(category="general_harms"),
                                  content=[], usage=usage())
        run = SearchRun.objects.create(tenant=self.acme, search=self.search, model="claude-opus-5-5")
        run = execute_run(run.id, client=FakeClient([refused], {}))
        self.assertEqual(run.status, "ERROR")
        self.assertIn("no quiso", run.error)


class ConvertTests(ProspectingCase):
    def test_convert_creates_contact_and_opportunity(self):
        p = Prospect.objects.create(tenant=self.acme, name="Ana Gómez", company="Ferretería Sol", need="CRM",
                                    source_url="https://reddit.com/x", source_name="Reddit", whatsapp="+595981000000")
        self.login(self.staff)
        res = self.client.post(f"/api/prospecting/prospects/{p.id}/convert/", {"amount": 5000000}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        lead = Lead.objects.get(pk=res.data["lead"])
        self.assertEqual((lead.status, lead.source, lead.phone), ("CONVERTIDO", "CAPTACION_WEB", "+595981000000"))
        self.assertIn("https://reddit.com/x", lead.description)
        self.assertEqual(Contact.objects.get(pk=res.data["contact"]).first_name, "Ana")
        self.assertEqual(Opportunity.objects.get(pk=res.data["opportunity"]).amount, 5000000)
        p.refresh_from_db()
        self.assertEqual(p.status, "CONVERTIDO")
        again = self.client.post(f"/api/prospecting/prospects/{p.id}/convert/", {}, format="json")
        self.assertEqual(again.status_code, 400)

    def test_status_changes(self):
        p = Prospect.objects.create(tenant=self.acme, need="CRM")
        self.login(self.staff)
        res = self.client.patch(f"/api/prospecting/prospects/{p.id}/", {"status": "CONTACTADO"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertIsNotNone(res.data["contacted_at"])
        res = self.client.patch(f"/api/prospecting/prospects/{p.id}/", {"status": "CONVERTIDO"}, format="json")
        self.assertEqual(res.status_code, 400)
