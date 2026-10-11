from rest_framework.routers import DefaultRouter

from .views import NoteViewSet, TaskViewSet, TimelineViewSet

notes_router = DefaultRouter()
notes_router.register("", NoteViewSet, basename="note")
notes_urlpatterns = notes_router.urls

tasks_router = DefaultRouter()
tasks_router.register("", TaskViewSet, basename="task")
tasks_urlpatterns = tasks_router.urls

timeline_router = DefaultRouter()
timeline_router.register("", TimelineViewSet, basename="timeline")
timeline_urlpatterns = timeline_router.urls
