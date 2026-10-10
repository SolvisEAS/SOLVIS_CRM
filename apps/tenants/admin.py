from django.contrib import admin

from .models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "frontend", "currency", "is_active", "created_at")
    search_fields = ("name", "slug")
    list_filter = ("is_active", "frontend")
    prepopulated_fields = {"slug": ("name",)}
