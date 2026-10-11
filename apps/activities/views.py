from rest_framework import viewsets

from core.tenancy import TenantScopedViewSetMixin

from .models import Note, Task, TimelineEvent
from .serializers import NoteSerializer, TaskSerializer
from .serializers_timeline import TimelineEventSerializer
from .timeline import log_event


class NoteViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    """Notas de un registro: GET /api/notes/?related_type=lead&related_id=5"""

    queryset = Note.objects.select_related("author").all()
    serializer_class = NoteSerializer
    filterset_fields = ("related_type", "related_id", "author")
    ordering_fields = ("created_at",)

    def get_create_defaults(self, serializer):
        return {"author": self.request.user}

    def perform_create(self, serializer):
        super().perform_create(serializer)
        note = serializer.instance
        log_event(note.tenant_id, note.related_type, note.related_id, "note", f"Agregó una nota: {note.body[:120]}", self.request.user)


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

    def perform_create(self, serializer):
        super().perform_create(serializer)
        task = serializer.instance
        log_event(task.tenant_id, task.related_type, task.related_id, "task", f"Creó la tarea: {task.title}", self.request.user)

    def perform_update(self, serializer):
        was = serializer.instance.status
        task = serializer.save()
        if was != task.status and task.status == Task.Status.COMPLETADA:
            log_event(task.tenant_id, task.related_type, task.related_id, "task", f"Completó la tarea: {task.title}", self.request.user)


class TimelineViewSet(TenantScopedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """Historial de un registro: GET /api/timeline/?related_type=lead&related_id=5"""

    queryset = TimelineEvent.objects.select_related("user").all()
    serializer_class = TimelineEventSerializer
    filterset_fields = ("related_type", "related_id")
