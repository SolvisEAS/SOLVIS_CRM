"""Al crear un cliente nuevo se le cargan las etapas de pipeline por defecto."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Tenant


@receiver(post_save, sender=Tenant)
def seed_stages_for_new_tenant(sender, instance, created, **kwargs):
    if created:
        from apps.opportunities.stages import seed_default_stages

        seed_default_stages(instance)
