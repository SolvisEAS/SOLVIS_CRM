from django.contrib import admin

from .models import Opportunity, PipelineStage


@admin.register(PipelineStage)
class PipelineStageAdmin(admin.ModelAdmin):
    list_display = ("name", "sequence", "probability", "is_won", "is_lost", "is_active")
    ordering = ("sequence",)


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "stage", "amount", "assigned_to")
    list_filter = ("stage", "company")
    search_fields = ("name",)
