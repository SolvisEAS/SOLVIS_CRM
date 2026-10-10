from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsAdministrador

from .serializers import TenantSettingsSerializer


class CurrentTenantView(APIView):
    """
    GET   /api/tenant/ -> datos del cliente del usuario
    PATCH /api/tenant/ -> editar nombre, colores, logo y moneda (solo ADMINISTRADOR)

    El slug y el front no se cambian desde acá: los define Solvis en el admin.
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.IsAuthenticated()]
        return [IsAdministrador()]

    def get_tenant(self, request):
        return request.user.tenant

    def get(self, request):
        tenant = self.get_tenant(request)
        if tenant is None:
            return Response({"detail": "El usuario no pertenece a ningún cliente."}, status=404)
        return Response(TenantSettingsSerializer(tenant).data)

    def patch(self, request):
        tenant = self.get_tenant(request)
        if tenant is None:
            return Response({"detail": "El usuario no pertenece a ningún cliente."}, status=404)
        serializer = TenantSettingsSerializer(tenant, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
