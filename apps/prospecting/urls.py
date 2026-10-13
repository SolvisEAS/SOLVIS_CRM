from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ProspectViewSet, SearchRunViewSet, SearchViewSet, SettingsTestView, SettingsView, StatsView

router = DefaultRouter()
router.register("searches", SearchViewSet, basename="prospecting-search")
router.register("runs", SearchRunViewSet, basename="prospecting-run")
router.register("prospects", ProspectViewSet, basename="prospecting-prospect")

urlpatterns = [
    path("settings/", SettingsView.as_view(), name="prospecting-settings"),
    path("settings/test/", SettingsTestView.as_view(), name="prospecting-settings-test"),
    path("stats/", StatsView.as_view(), name="prospecting-stats"),
    *router.urls,
]
