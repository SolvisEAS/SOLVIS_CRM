"""
Aislamiento por cliente (multi-tenant) para la API.

- TenantScopedViewSetMixin: cada ViewSet solo ve y crea registros del
  tenant del usuario autenticado.
- TenantScopedSerializerMixin: los campos relacionados (empresa,
  contacto, etapa, usuario asignado…) solo aceptan registros del mismo
  tenant, así nadie puede apuntar a datos de otro cliente.
"""


def user_tenant_id(user):
    return getattr(user, "tenant_id", None) if user and user.is_authenticated else None


def has_tenant_field(model):
    return any(f.name == "tenant" for f in model._meta.get_fields())


class TenantScopedViewSetMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        tenant_id = user_tenant_id(self.request.user)
        if tenant_id is None:
            return qs.none()
        return qs.filter(tenant_id=tenant_id)

    def get_create_defaults(self, serializer):
        """Valores extra al crear (ej: owner = quien crea). Lo sobrescriben las vistas."""
        return {}

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=user_tenant_id(self.request.user),
            **self.get_create_defaults(serializer),
        )


class TenantScopedSerializerMixin:
    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        tenant_id = user_tenant_id(getattr(request, "user", None))
        for field in fields.values():
            queryset = getattr(field, "queryset", None)
            if queryset is None or not has_tenant_field(queryset.model):
                continue
            field.queryset = (
                queryset.none() if tenant_id is None else queryset.filter(tenant_id=tenant_id)
            )
        return fields
