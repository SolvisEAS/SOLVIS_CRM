"""
URLs raíz de SOLVIS CRM.

Toda la API vive bajo el prefijo /api/, tal como se definió en el
punto 14 del documento de arquitectura. Cada app agrega sus propias
rutas dentro de /api/<recurso>/.
"""
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
)

from apps.activities.urls import notes_urlpatterns, tasks_urlpatterns
from apps.opportunities.urls import pipeline_stage_urlpatterns
from apps.tenants.views import CurrentTenantView
from core.views import DashboardView, MetaView

admin.site.site_header = "Solvis CRM · Administración"
admin.site.site_title = "Solvis CRM"
admin.site.index_title = "Panel de administración"

urlpatterns = [
    path("admin/", admin.site.urls),

    # Autenticación JWT: /api/auth/login/, /api/auth/refresh/, /api/auth/logout/
    path("api/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/logout/", TokenBlacklistView.as_view(), name="token_blacklist"),

    # Recursos de la app de usuarios: /api/users/...
    path("api/users/", include("apps.users.urls")),

    # Fase 2 — CRM básico (punto 14 del documento)
    path("api/companies/", include("apps.companies.urls")),
    path("api/contacts/", include("apps.contacts.urls")),
    path("api/opportunities/", include("apps.opportunities.urls")),
    path("api/pipeline-stages/", include(pipeline_stage_urlpatterns)),
    path("api/leads/", include("apps.leads.urls")),

    # Fase 3 — actividades, y endpoints del front (inicio y catálogos)
    path("api/notes/", include(notes_urlpatterns)),
    path("api/tasks/", include(tasks_urlpatterns)),
    path("api/dashboard/", DashboardView.as_view(), name="dashboard"),
    path("api/meta/", MetaView.as_view(), name="meta"),
    path("api/tenant/", CurrentTenantView.as_view(), name="current-tenant"),
]
