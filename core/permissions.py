"""
Sistema base de permisos (punto 12 del documento de arquitectura).

Esta es la base mínima para la Fase 1: los roles existen y se pueden
consultar, pero las reglas granulares por módulo (quién crea, edita,
elimina cada entidad) se van a ir agregando en las Fases 2 y 3, a
medida que existan esos módulos.
"""
from rest_framework.permissions import BasePermission


class IsAdministrador(BasePermission):
    """Solo usuarios con rol ADMINISTRADOR."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == request.user.Roles.ADMINISTRADOR
        )


class IsGerenteOrAdministrador(BasePermission):
    """Usuarios con rol GERENTE o ADMINISTRADOR."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user.role in (
            request.user.Roles.ADMINISTRADOR,
            request.user.Roles.GERENTE,
        )
