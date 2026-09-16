from django.contrib import admin

from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "city", "country", "owner")
    search_fields = ("name", "email")
    list_filter = ("country", "city")
