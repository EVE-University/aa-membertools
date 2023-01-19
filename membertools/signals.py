from django.db.models.signals import pre_save
from django.dispatch import receiver

from allianceauth.authentication.models import UserProfile

from .models import ApplicationTitle, Character, Member

from allianceauth.services.hooks import get_extension_logger

logger = get_extension_logger(__name__)


@receiver(pre_save, sender=UserProfile)
def change_main_hook(instance, **kwargs):
    if not instance.id:
        return

    old_instance = UserProfile.objects.get(id=instance.id)

    try:
        member = Member.objects.get(
            main_character__character_ownership__user=instance.user
        )
    except Member.DoesNotExist:
        # Nothing to do if there is no Member record for this user.
        return

    if instance.main_character != old_instance.main_character:
        logger.info(
            "%s changing main from %s to %s.",
            instance.user,
            instance.main_character.character_name,
            old_instance.main_character.character_name,
        )
        member.main_character = instance.main_character
        member.save()


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
