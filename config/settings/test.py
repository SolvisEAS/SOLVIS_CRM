"""Configuración para correr las pruebas: base SQLite en memoria, sin PostgreSQL."""
import os

os.environ.setdefault("DJANGO_SECRET_KEY", "pruebas-no-usar-en-produccion")
os.environ.setdefault("POSTGRES_DB", "x")
os.environ.setdefault("POSTGRES_USER", "x")
os.environ.setdefault("POSTGRES_PASSWORD", "x")

from .base import *  # noqa: E402,F401,F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": {"login": "1000/min"}}  # noqa: F405
