# Django
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

# Alliance Auth
from allianceauth.authentication.models import UserProfile
from allianceauth.services.hooks import get_extension_logger

from .app_settings import MEMBERTOOLS_MAIN_CORP_ID
from .models import Character, Member, _get_app_title_none

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

    if (
        instance.main_character
        and instance.main_character != old_instance.main_character
    ):
        logger.info(
            "%s changing main from %s to %s.",
            instance.user,
            instance.main_character.character_name,
            old_instance.main_character.character_name
            if old_instance.main_character
            else "(Unknown)",
        )
        member.main_character = instance.main_character
        member.save()


@receiver(pre_save, sender=Character)
def corp_change_hook(instance, **kwargs):
    if not instance.id:
        # Ignore new objects
        return
    old_instance = Character.objects.get(id=instance.id)

    try:
        if (
            instance.corporation.corporation_id
            == old_instance.corporation.corporation_id
        ):
            # No corp change, so nothing to do.
            return
    except AttributeError:
        return

    logger.info(
        "%s corp change from %s to %s, removing applied titles.",
        instance,
        old_instance.corporation,
        instance.corporation,
    )
    instance.applied_title = _get_app_title_none()

    # TODO: Should this be broken out into a task?
    if instance.corporation.corporation_id == MEMBERTOOLS_MAIN_CORP_ID:
        try:
            member = Member.objects.get(
                main_character__character_ownership__user=instance.eve_character.character_ownership.user
            )
        except Member.DoesNotExist:
            # TODO: New corp member without coming through tool. Maybe generate a warning notice to admins
            # or may a message center inside the tool.
            logger.warning(
                "%s joined main corp outside of this tool", instance.character_name
            )
            return

        member.last_joined = timezone.now()

        if member.first_joined is None:
            member.first_joined = member.last_joined

        member.save()
