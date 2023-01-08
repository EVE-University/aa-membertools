from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import Application, ApplicationTitle, Character

from allianceauth.services.hooks import get_extension_logger

logger = get_extension_logger(__name__)


@receiver(pre_save, sender=Character)
def left_corp_hook(instance, **kwargs):
    if not instance.id:
        # Ignore new objects
        return
    old_instance = Character.objects.get(id=instance.id)

    if instance.corporation != old_instance.corporation:
        logger.info(
            "%s corp change from %s to %s, removing applied titles.",
            instance,
            old_instance.corporation,
            instance.corporation,
        )
        instance.applied_title, _ = ApplicationTitle.objects.get_or_create(
            name="None", priority=0
        )
