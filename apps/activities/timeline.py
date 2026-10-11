"""Registro del historial de cambios de cada registro del CRM."""


def log_event(tenant_id, related_type, related_id, verb, description, user=None):
    from .models import TimelineEvent

    if not (tenant_id and related_type and related_id):
        return None
    return TimelineEvent.objects.create(
        tenant_id=tenant_id, related_type=related_type, related_id=related_id,
        verb=verb, description=description[:500], user=user if user and user.is_authenticated else None,
    )


def display(instance, field_name):
    """Valor legible de un campo (opciones con su etiqueta, relaciones con su nombre)."""
    field = instance._meta.get_field(field_name)
    if field.choices:
        return getattr(instance, f"get_{field_name}_display")() or "—"
    value = getattr(instance, field_name)
    if value in (None, ""):
        return "—"
    if field.get_internal_type() == "DecimalField":
        return f"{value:,.0f}".replace(",", ".")
    return str(value)


def snapshot(instance, fields):
    return {name: display(instance, name) for name in fields}
