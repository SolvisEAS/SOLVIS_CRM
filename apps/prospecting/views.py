"""
API de la Captación. Solo para el personal de Solvis (is_staff) y siempre
dentro de su propio cliente.

GET/PUT    /api/prospecting/settings/          clave de Anthropic (nunca se devuelve), modelo y tope
POST       /api/prospecting/settings/test/     prueba la clave sin gastar
GET        /api/prospecting/stats/             números para el tablero
CRUD       /api/prospecting/searches/          búsquedas guardadas
POST       /api/prospecting/searches/{id}/run/ Claude sale a buscar (en segundo plano)
GET        /api/prospecting/runs/?search=      ejecuciones (para ver el avance)
CRUD       /api/prospecting/prospects/         ?status= ?search_id= ?min_score= ?has_contact=1 ?search=texto
POST       /api/prospecting/prospects/{id}/convert/  -> Lead + Empresa + Contacto (+ Oportunidad)
"""
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, F, Q
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.activities.timeline import log_event
from apps.leads.models import Lead
from apps.leads.serializers import LeadConvertSerializer
from apps.leads.services import convert_lead
from core.exceptions import BusinessRuleError
from core.tenancy import TenantScopedViewSetMixin, user_tenant_id

from . import engine
from .models import Prospect, Search, SearchRun
from .runner import api_key_for, clean_email, close_stale_runs, get_settings, month_spend, start_run
from .serializers import ProspectSerializer, SearchRunSerializer, SearchSerializer, SettingsSerializer

CONTACT_LABELS = {
    "email": "Correo", "phone": "Teléfono", "whatsapp": "WhatsApp", "instagram": "Instagram",
    "facebook": "Facebook", "linkedin": "LinkedIn", "twitter": "X/Twitter", "website": "Web",
    "other_contact": "Otro",
}


def settings_payload(tenant_id):
    cfg = get_settings(tenant_id)
    key = api_key_for(cfg)
    return {
        "has_api_key": bool(key),
        "api_key_hint": f"…{key[-4:]}" if key else "",
        "api_key_from_server": bool(key) and not cfg.anthropic_api_key,
        "model": cfg.model,
        "models": [{"value": v, "label": label} for v, label in cfg.Model.choices],
        "monthly_budget_usd": str(cfg.monthly_budget_usd),
        "month_spend_usd": str(month_spend(tenant_id).quantize(Decimal("0.01"))),
    }


class SettingsView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request):
        return Response(settings_payload(user_tenant_id(request.user)))

    def put(self, request):
        tenant_id = user_tenant_id(request.user)
        serializer = SettingsSerializer(get_settings(tenant_id), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(settings_payload(tenant_id))

    patch = put


class SettingsTestView(APIView):
    permission_classes = (IsAdminUser,)

    def post(self, request):
        cfg = get_settings(user_tenant_id(request.user))
        key = (request.data.get("api_key") or "").strip() or api_key_for(cfg)
        if not key:
            raise BusinessRuleError("Todavía no cargaste la clave de Anthropic.", "missing_api_key")
        try:
            name = engine.check_key(key, request.data.get("model") or cfg.model)
        except engine.EngineError as ex:
            raise BusinessRuleError(str(ex), "api_key_check_failed") from ex
        return Response({"ok": True, "model": name})


class StatsView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request):
        tenant_id = user_tenant_id(request.user)
        prospects = Prospect.objects.filter(tenant_id=tenant_id)
        by_status = dict(prospects.values_list("status").annotate(n=Count("id")).values_list("status", "n"))
        sources = (prospects.exclude(source_name="").values("source_name").annotate(count=Count("id"))
                   .order_by("-count")[:8])
        week_ago = timezone.now() - timedelta(days=7)
        cfg = get_settings(tenant_id)
        return Response({
            "total": prospects.count(),
            "by_status": {s: by_status.get(s, 0) for s in Prospect.Status.values},
            "new_this_week": prospects.filter(created_at__gte=week_ago).count(),
            "with_contact": prospects.filter(
                Q(email__gt="") | Q(phone__gt="") | Q(whatsapp__gt="") | Q(instagram__gt="")
                | Q(facebook__gt="") | Q(linkedin__gt="") | Q(twitter__gt="") | Q(website__gt="")
                | Q(other_contact__gt="")).count(),
            "sources": [{"name": s["source_name"], "count": s["count"]} for s in sources],
            "month_spend_usd": str(month_spend(tenant_id).quantize(Decimal("0.01"))),
            "monthly_budget_usd": str(cfg.monthly_budget_usd),
            "has_api_key": bool(api_key_for(cfg)),
        })


class StaffScopedMixin(TenantScopedViewSetMixin):
    permission_classes = (IsAdminUser,)


class SearchViewSet(StaffScopedMixin, viewsets.ModelViewSet):
    queryset = Search.objects.annotate(prospects_count=Count("prospects"))
    serializer_class = SearchSerializer
    pagination_class = None
    search_fields = ("name", "keywords")
    ordering_fields = ("name", "created_at")

    def get_create_defaults(self, serializer):
        return {"created_by": self.request.user}

    @action(detail=True, methods=["post"])
    def run(self, request, pk=None):
        run = start_run(self.get_object(), request.user)
        return Response(SearchRunSerializer(run).data, status=status.HTTP_202_ACCEPTED)


class SearchRunViewSet(StaffScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = SearchRun.objects.select_related("search")
    serializer_class = SearchRunSerializer
    filterset_fields = ("search", "status")

    def get_queryset(self):
        close_stale_runs(user_tenant_id(self.request.user))
        return super().get_queryset()


class ProspectViewSet(StaffScopedMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin,
                      mixins.DestroyModelMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Prospect.objects.select_related("search", "lead")
    serializer_class = ProspectSerializer
    search_fields = ("name", "company", "need", "quote", "source_name", "location", "notes")
    ordering_fields = ("created_at", "score", "published_at", "status")

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("search_id"):
            qs = qs.filter(search_id=params["search_id"])
        if params.get("min_score"):
            qs = qs.filter(score__gte=int(params["min_score"]) if params["min_score"].isdigit() else 0)
        if params.get("has_contact") == "1":
            q = Q()
            for name in Prospect.CONTACT_FIELDS:
                q |= Q(**{f"{name}__gt": ""})
            qs = qs.filter(q)
        return qs

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)
        # Los que no tienen fecha de publicación van al final, no al principio.
        if self.request.query_params.get("ordering") == "-published_at":
            qs = qs.order_by(F("published_at").desc(nulls_last=True), "-created_at")
        return qs

    def get_create_defaults(self, serializer):
        return {"assigned_to": serializer.validated_data.get("assigned_to") or self.request.user}

    def perform_update(self, serializer):
        becomes_contacted = (serializer.validated_data.get("status") == Prospect.Status.CONTACTADO
                             and serializer.instance.contacted_at is None)
        prospect = serializer.save()
        if becomes_contacted:
            prospect.contacted_at = timezone.now()
            prospect.save(update_fields=["contacted_at"])

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        prospect = self.get_object()
        if prospect.status == Prospect.Status.CONVERTIDO:
            raise BusinessRuleError("Este prospecto ya fue convertido.", "prospect_already_converted")
        params = LeadConvertSerializer(data=request.data)
        params.is_valid(raise_exception=True)
        with transaction.atomic():
            lead = Lead.objects.create(
                tenant_id=prospect.tenant_id, title=(prospect.need or "Prospecto de Captación")[:255],
                name=(prospect.name or prospect.company or "Prospecto")[:255],
                email=clean_email(prospect.email), phone=(prospect.phone or prospect.whatsapp)[:50],
                company=prospect.company[:255], source=Lead.Source.CAPTACION_WEB,
                status=Lead.Status.CALIFICADO, assigned_to=prospect.assigned_to or request.user,
                description=lead_description(prospect),
            )
            log_event(lead.tenant_id, "lead", lead.id, "created",
                      f"Creado desde Captación ({prospect.source_name or 'web'})", request.user)
            company, contact, opportunity = convert_lead(lead, request.user, **params.validated_data)
            prospect.status = Prospect.Status.CONVERTIDO
            prospect.lead = lead
            prospect.save(update_fields=["status", "lead", "updated_at"])
        return Response({"prospect": ProspectSerializer(prospect).data, "lead": lead.id, "company": company.id,
                         "contact": contact.id, "opportunity": opportunity.id if opportunity else None})


def lead_description(p):
    contacts = " · ".join(f"{CONTACT_LABELS[f]}: {getattr(p, f)}" for f in Prospect.CONTACT_FIELDS if getattr(p, f))
    lines = [
        "Encontrado por Captación web.",
        f"Qué necesita: {p.need}",
        f"Lo que dijo: \"{p.quote}\"" if p.quote else "",
        f"Origen: {p.source_name or 'web'} — {p.source_url}" if p.source_url else "",
        f"Publicado: {p.published_at:%d/%m/%Y}" if p.published_at else "",
        f"Ubicación: {p.location}" if p.location else "",
        f"Contactos: {contacts}" if contacts else "",
        f"Notas: {p.notes}" if p.notes else "",
    ]
    return "\n".join(line for line in lines if line)
