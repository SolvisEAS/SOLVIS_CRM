from django.contrib import admin

from .models import Note, Task


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("related_type", "related_id", "author", "tenant", "created_at")
    list_filter = ("related_type", "tenant")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "priority", "due_date", "assigned_to", "tenant")
    list_filter = ("status", "priority", "tenant")
    search_fields = ("title",)
