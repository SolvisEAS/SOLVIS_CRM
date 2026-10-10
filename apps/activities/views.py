from rest_framework import viewsets

from core.tenancy import TenantScopedViewSetMixin

from .models import Note, Task
from .serializers import NoteSerializer, TaskSerializer


class NoteViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    """Notas de un registro: GET /api/notes/?related_type=lead&related_id=5"""

    queryset = Note.objects.select_related("author").all()
    serializer_class = NoteSerializer
    filterset_fields = ("related_type", "related_id", "author")
    ordering_fields = ("created_at",)

    def get_create_defaults(self, serializer):
        return {"author": self.request.user}


class TaskViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    """Tareas: GET /api/tasks/?status=PENDIENTE&assigned_to=<id>"""

    queryset = Task.objects.select_related("assigned_to").all()
    serializer_class = TaskSerializer
    search_fields = ("title", "description")
    filterset_fields = ("status", "priority", "related_type", "related_id", "assigned_to")
    ordering_fields = ("due_date", "created_at", "priority", "status")

    def get_create_defaults(self, serializer):
        if serializer.validated_data.get("assigned_to") is None:
            return {"assigned_to": self.request.user}
        return {}
