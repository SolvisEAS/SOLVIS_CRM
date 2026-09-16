from rest_framework import viewsets

from .models import Contact
from .serializers import ContactSerializer


class ContactViewSet(viewsets.ModelViewSet):
    """CRUD completo de Contactos. Permite filtrar por ?company=<id>."""

    queryset = Contact.objects.select_related("company", "owner").all()
    serializer_class = ContactSerializer
    search_fields = ("first_name", "last_name", "email")
    filterset_fields = ("company", "owner")
    ordering_fields = ("last_name", "created_at")

    def perform_create(self, serializer):
        if serializer.validated_data.get("owner") is None:
            serializer.save(owner=self.request.user)
        else:
            serializer.save()
