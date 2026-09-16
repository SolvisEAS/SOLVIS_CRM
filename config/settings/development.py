"""Configuración específica de desarrollo local."""
from .base import *  # noqa: F401,F403

DEBUG = True

INSTALLED_APPS += [  # noqa: F405
    "django_extensions",
]

# En desarrollo es útil ver el detalle completo de errores de la API.
REST_FRAMEWORK = {  # noqa: F405
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
}
