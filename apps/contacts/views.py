from rest_framework import viewsets

from core.tenancy import TenantScopedViewSetMixin

from .models import Contact
from .serializers import ContactSerializer


class ContactViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    """CRUD completo de Contactos. Permite filtrar por ?company=<id>."""

    queryset = Contact.objects.select_related("company", "owner").all()
    serializer_class = ContactSerializer
    search_fields = ("first_name", "last_name", "email", "phone", "company__name")
    filterset_fields = ("company", "owner")
    ordering_fields = ("last_name", "first_name", "created_at")
    timeline_type = "contact"
    tracked_fields = {"company": "Empresa", "owner": "Propietario", "position": "Cargo",
                      "email": "Correo", "phone": "Teléfono"}

    def get_create_defaults(self, serializer):
        if serializer.validated_data.get("owner") is None:
            return {"owner": self.request.user}
        return {}
