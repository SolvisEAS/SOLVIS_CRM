from rest_framework.permissions import BasePermission


class IsSelf(BasePermission):
    """Permite la acción solo si el objeto es el propio usuario autenticado.

    Placeholder para la Fase 1. Se va a usar cuando agreguemos, por
    ejemplo, edición de perfil o cambio de contraseña propio.
    """

    def has_object_permission(self, request, view, obj):
        return obj == request.user
