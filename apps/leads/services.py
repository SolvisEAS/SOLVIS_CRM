"""
Conversión de un Lead en Empresa + Contacto (+ Oportunidad), como el
"Convertir" de Zoho CRM. La usan la API de Leads y la Captación del
Panel Solvis (un prospecto encontrado en internet pasa por un Lead).
"""
from django.db import transaction
from django.utils import timezone

from apps.activities.timeline import log_event
from apps.companies.models import Company
from apps.contacts.models import Contact
from apps.opportunities.models import Opportunity, PipelineStage
from core.exceptions import BusinessRuleError

from .models import Lead


def convert_lead(lead, user, create_opportunity=True, opportunity_name="", amount=0,
                 expected_closing_date=None, stage=None):
    """Devuelve (company, contact, opportunity|None). Falla si el lead ya estaba convertido."""
    if lead.status == Lead.Status.CONVERTIDO:
        raise BusinessRuleError("Este lead ya fue convertido.", "lead_already_converted")
    tenant_id = lead.tenant_id
    owner = lead.assigned_to or user

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
        if create_opportunity:
            stages = PipelineStage.objects.filter(tenant_id=tenant_id, is_active=True)
            chosen = stages.filter(pk=stage).first() if stage else None
            chosen = chosen or stages.filter(is_won=False, is_lost=False).order_by("sequence").first()
            if chosen is None:
                raise BusinessRuleError("No hay etapas de pipeline configuradas.", "no_pipeline_stages")
            opportunity = Opportunity.objects.create(
                tenant_id=tenant_id, name=opportunity_name or lead.title,
                company=company, contact=contact, amount=amount or 0,
                probability=chosen.probability, expected_closing_date=expected_closing_date,
                stage=chosen, assigned_to=owner, description=lead.description,
            )
        lead.status = Lead.Status.CONVERTIDO
        lead.converted_at = timezone.now()
        lead.converted_company = company
        lead.converted_contact = contact
        lead.converted_opportunity = opportunity
        lead.save()

        created = ", ".join(filter(None, [f"empresa {company.name}", f"contacto {contact}",
                                          f"oportunidad {opportunity.name}" if opportunity else None]))
        log_event(tenant_id, "lead", lead.id, "converted", f"Convirtió el lead: {created}", user)
        log_event(tenant_id, "contact", contact.id, "created", f"Creado al convertir el lead {lead.name}", user)
        if opportunity:
            log_event(tenant_id, "opportunity", opportunity.id, "created",
                      f"Creada al convertir el lead {lead.name}", user)
    return company, contact, opportunity
