"""Endpoints transversales: tablero de inicio y catálogos para el front."""

from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.activities.models import RelatedType, Task
from apps.companies.models import Company
from apps.contacts.models import Contact
from apps.leads.models import Lead
from apps.opportunities.models import Opportunity, PipelineStage
from apps.users.models import User

from .tenancy import user_tenant_id


def choices(text_choices):
    return [{"value": value, "label": label} for value, label in text_choices.choices]


class MetaView(APIView):
    """GET /api/meta/ — opciones de los campos de selección (estado, origen, rol…)."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response(
            {
                "lead_status": choices(Lead.Status),
                "lead_source": choices(Lead.Source),
                "task_status": choices(Task.Status),
                "task_priority": choices(Task.Priority),
                "related_type": choices(RelatedType),
                "user_role": choices(User.Roles),
            }
        )


class DashboardView(APIView):
    """GET /api/dashboard/ — números del inicio, solo del cliente del usuario."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        tenant_id = user_tenant_id(request.user)
        if tenant_id is None:
            return Response({"detail": "El usuario no pertenece a ningún cliente."}, status=403)

        today = timezone.localdate()
        month_start = today.replace(day=1)
        leads = Lead.objects.filter(tenant_id=tenant_id)
        opps = Opportunity.objects.filter(tenant_id=tenant_id)
        open_opps = opps.filter(stage__is_won=False, stage__is_lost=False)
        closed_month = opps.filter(closed_at__date__gte=month_start)
        won_month = closed_month.filter(stage__is_won=True)
        lost_month = closed_month.filter(stage__is_lost=True)
        total_leads = leads.count()
        converted = leads.filter(status=Lead.Status.CONVERTIDO).count()

        pipeline = (
            PipelineStage.objects.filter(tenant_id=tenant_id, is_active=True)
            .annotate(count=Count("opportunities"), amount=Sum("opportunities__amount"))
            .order_by("sequence")
        )
        my_tasks = Task.objects.filter(
            tenant_id=tenant_id, assigned_to=request.user
        ).exclude(status=Task.Status.COMPLETADA)

        return Response(
            {
                "totals": {
                    "leads": total_leads,
                    "leads_new": leads.filter(status=Lead.Status.NUEVO).count(),
                    "companies": Company.objects.filter(tenant_id=tenant_id).count(),
                    "contacts": Contact.objects.filter(tenant_id=tenant_id).count(),
                    "open_opportunities": open_opps.count(),
                    "open_amount": open_opps.aggregate(s=Sum("amount"))["s"] or 0,
                    "won_month_count": won_month.count(),
                    "won_month_amount": won_month.aggregate(s=Sum("amount"))["s"] or 0,
                    "lost_month_count": lost_month.count(),
                    "conversion_rate": round(converted * 100 / total_leads) if total_leads else 0,
                    "leads_converted": converted,
                    "tasks_pending": my_tasks.count(),
                    "tasks_overdue": my_tasks.filter(due_date__lt=today).count(),
                },
                "leads_by_status": list(leads.values("status").annotate(count=Count("id")).order_by("status")),
                "leads_by_source": list(
                    leads.exclude(source="").values("source").annotate(count=Count("id")).order_by("-count")
                ),
                "pipeline": [
                    {
                        "id": s.id, "name": s.name, "color": s.color, "is_won": s.is_won,
                        "is_lost": s.is_lost, "count": s.count, "amount": s.amount or 0,
                    }
                    for s in pipeline
                ],
                "closing_this_month": list(
                    open_opps.filter(expected_closing_date__gte=month_start,
                                     expected_closing_date__month=today.month,
                                     expected_closing_date__year=today.year)
                    .order_by("expected_closing_date")
                    .values("id", "name", "amount", "expected_closing_date", "company__name", "stage__name")[:8]
                ),
                "my_tasks": list(
                    my_tasks.order_by("due_date").values("id", "title", "due_date", "priority", "status",
                                                          "related_type", "related_id")[:8]
                ),
                "recent_leads": list(
                    leads.order_by("-created_at").values("id", "title", "name", "company", "status", "created_at")[:6]
                ),
            }
        )
