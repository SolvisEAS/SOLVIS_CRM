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

from apps.opportunities.urls import pipeline_stage_urlpatterns

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
]
