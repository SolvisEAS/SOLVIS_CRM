from rest_framework import serializers

from core.tenancy import TenantScopedSerializerMixin

from .models import Note, Task


class NoteSerializer(TenantScopedSerializerMixin, serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Note
        fields = ("id", "related_type", "related_id", "body", "author", "author_name", "created_at", "updated_at")
        read_only_fields = ("id", "author", "created_at", "updated_at")

    def get_author_name(self, obj):
        return (obj.author.get_full_name() or obj.author.username) if obj.author else None


class TaskSerializer(TenantScopedSerializerMixin, serializers.ModelSerializer):
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = (
            "id", "title", "description", "due_date", "status", "priority",
            "related_type", "related_id", "assigned_to", "assigned_to_name",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_assigned_to_name(self, obj):
        return (obj.assigned_to.get_full_name() or obj.assigned_to.username) if obj.assigned_to else None
