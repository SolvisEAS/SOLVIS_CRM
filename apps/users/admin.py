from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Permite administrar usuarios y su rol desde /admin/."""

    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Rol en el CRM", {"fields": ("role", "tenant")}),
    )
    list_display = ("username", "email", "first_name", "last_name", "role", "tenant", "is_staff")
    list_filter = DjangoUserAdmin.list_filter + ("role", "tenant")
