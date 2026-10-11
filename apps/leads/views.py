from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.activities.timeline import log_event
from apps.companies.models import Company
from apps.contacts.models import Contact
from apps.opportunities.models import Opportunity, PipelineStage
from core.exceptions import BusinessRuleError
from core.tenancy import TenantScopedViewSetMixin

from .models import Lead
from .serializers import LeadSerializer


class LeadConvertSerializer(serializers.Serializer):
    create_opportunity = serializers.BooleanField(default=True)
    opportunity_name = serializers.CharField(required=False, allow_blank=True)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, default=0)
    expected_closing_date = serializers.DateField(required=False, allow_null=True)
    stage = serializers.IntegerField(required=False, allow_null=True)


class LeadViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    """
    CRUD completo de Leads. Permite filtrar por
    ?status=<status>, ?source=<source>, ?assigned_to=<id>.

    POST /api/leads/{id}/convert/ convierte el Lead en Empresa +
    Contacto (+ Oportunidad opcional), como el "Convertir" de Zoho CRM.
    """

    queryset = Lead.objects.select_related("assigned_to").all()
    serializer_class = LeadSerializer
    search_fields = ("title", "name", "email", "phone", "company")
    filterset_fields = ("status", "source", "assigned_to")
    ordering_fields = ("created_at", "status", "name", "company")
    timeline_type = "lead"
    tracked_fields = {"status": "Estado", "assigned_to": "Propietario", "source": "Origen",
                      "title": "Título", "company": "Empresa", "email": "Correo", "phone": "Teléfono"}

    def get_create_defaults(self, serializer):
        if serializer.validated_data.get("assigned_to") is None:
            return {"assigned_to": self.request.user}
        return {}

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        lead = self.get_object()
        if lead.status == Lead.Status.CONVERTIDO:
            raise BusinessRuleError("Este lead ya fue convertido.", "lead_already_converted")
        params = LeadConvertSerializer(data=request.data)
        params.is_valid(raise_exception=True)
        opts = params.validated_data
        tenant_id = lead.tenant_id
        owner = lead.assigned_to or request.user

        with transaction.atomic():
            company_name = lead.company.strip() or lead.name
            company = Company.objects.filter(tenant_id=tenant_id, name__iexact=company_name).first()
            if company is None:
                company = Company.objects.create(
                    tenant_id=tenant_id, name=company_name, email=lead.email if not lead.company else "",
                    phone=lead.phone if not lead.company else "", owner=owner,
                )
            first_name, _, last_name = lead.name.strip().partition(" ")
            contact = Contact.objects.create(
                tenant_id=tenant_id, first_name=first_name or lead.name, last_name=last_name,
                email=lead.email, phone=lead.phone, company=company, owner=owner,
            )
            opportunity = None
            if opts["create_opportunity"]:
                stages = PipelineStage.objects.filter(tenant_id=tenant_id, is_active=True)
                stage = stages.filter(pk=opts.get("stage")).first() if opts.get("stage") else None
                stage = stage or stages.filter(is_won=False, is_lost=False).order_by("sequence").first()
                if stage is None:
                    raise BusinessRuleError("No hay etapas de pipeline configuradas.", "no_pipeline_stages")
                opportunity = Opportunity.objects.create(
                    tenant_id=tenant_id, name=opts.get("opportunity_name") or lead.title,
                    company=company, contact=contact, amount=opts.get("amount") or 0,
                    probability=stage.probability, expected_closing_date=opts.get("expected_closing_date"),
                    stage=stage, assigned_to=owner, description=lead.description,
                )
            lead.status = Lead.Status.CONVERTIDO
            lead.converted_at = timezone.now()
            lead.converted_company = company
            lead.converted_contact = contact
            lead.converted_opportunity = opportunity
            lead.save()

            created = ", ".join(filter(None, [f"empresa {company.name}", f"contacto {contact}",
                                              f"oportunidad {opportunity.name}" if opportunity else None]))
            log_event(tenant_id, "lead", lead.id, "converted", f"Convirtió el lead: {created}", request.user)
            log_event(tenant_id, "contact", contact.id, "created", f"Creado al convertir el lead {lead.name}", request.user)
            if opportunity:
                log_event(tenant_id, "opportunity", opportunity.id, "created",
                          f"Creada al convertir el lead {lead.name}", request.user)

        return Response(
            {
                "lead": LeadSerializer(lead, context=self.get_serializer_context()).data,
                "company": company.id,
                "contact": contact.id,
                "opportunity": opportunity.id if opportunity else None,
            },
            status=status.HTTP_200_OK,
        )
