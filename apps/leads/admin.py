from django.contrib import admin

from .models import Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("title", "name", "company", "status", "source", "assigned_to")
    list_filter = ("status", "source")
    search_fields = ("title", "name", "email", "company")
