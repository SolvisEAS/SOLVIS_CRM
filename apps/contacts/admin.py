from django.contrib import admin

from .models import Contact


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "company", "owner")
    search_fields = ("first_name", "last_name", "email")
    list_filter = ("company",)
