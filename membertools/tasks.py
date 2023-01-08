import pprint

from datetime import timedelta
from celery import shared_task

from bravado.exception import (
    HTTPBadGateway,
    HTTPGatewayTimeout,
    HTTPServiceUnavailable,
    HTTPNotFound,
)

from django.db.models import Q
from django.http import HttpResponseNotFound
from django.utils import timezone
from pyparsing import Char

from allianceauth.services.hooks import get_extension_logger
from allianceauth.services.tasks import QueueOnce

from esi.errors import DjangoEsiException
from esi.models import Token

from .models import Member, Character, CharacterUpdateStatus

logger = get_extension_logger(__name__)

TASK_DEFAULT_KWARGS = {
    "time_limit": 1200,
    "max_retries": 3,
}

TASK_ESI_KWARGS = {
    **TASK_DEFAULT_KWARGS,
    **{
        "bind": True,
        "autoretry_for": (
            OSError,
            HTTPBadGateway,
            HTTPGatewayTimeout,
            HTTPServiceUnavailable,
        ),
        "retry_backoff": 30,
        "retry_kwargs": {"max_retries": 3},
    },
}


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 5},
)
def open_newmail_window(self, recipients, subject, body, token_id):
    token = Token.objects.get(id=token_id)
    client = token.get_esi_client()

    call = client.User_Interface.post_ui_openwindow_newmail(
        new_mail={"body": body, "recipients": recipients, "subject": subject}
    )
    call.request_config.also_return_response = True

    _, res = call.results()

    if res.status_code != 204:
        raise DjangoEsiException
    return True


@shared_task(**TASK_DEFAULT_KWARGS)
def update_all_characters(force=False):
    if force:
        query = Member.objects.values_list("id", flat=True)
    else:
        query = Member.objects.filter(
            Q(first_joined__isnull=True) | Q(last_joined__isnull=True)
        ).values_list("id", flat=True)
    for member_id in query:
        update_member.apply_async(kwargs={"member_id": member_id, "force": force})

    if force:
        query = Character.objects.values_list("id", flat=True)
    else:
        query = (
            Character.objects.filter(
                Q(update_status__isnull=True)
                | Q(update_status__expires_on__isnull=True)
                | Q(update_status__expires_on__lte=timezone.now())
            )
            .exclude(deleted=True)
            .values_list("id", flat=True)
        )
    for character_id in query:
        logger.debug(character_id)
        update_character.apply_async(
            kwargs={"character_id": character_id, "force": force}
        )


@shared_task(**{**TASK_ESI_KWARGS, **{"bind": True}})
def update_member(self, member_id, force=False):
    logger.debug("Task update_member() called!")
    member = Member.objects.get(pk=member_id)

    return member.update_joined_dates()


@shared_task(**{**TASK_ESI_KWARGS, **{"bind": True}})
def update_character(self, character_id, force=False):
    logger.debug("Task update_character() called!")
    character = Character.objects.get(pk=character_id)
    update_status, __ = CharacterUpdateStatus.objects.get_or_create(
        character=character,
        defaults={"character": character, "status": CharacterUpdateStatus.STATUS_OKAY},
    )
    logger.debug(
        "Character %s last updated %s, expires %s. (Force: %s)",
        character,
        update_status.updated_on,
        update_status.expires_on,
        force,
    )

    if (
        not force
        and update_status.expires_on
        and update_status.expires_on >= timezone.now()
    ):
        return False

    update_status.status = CharacterUpdateStatus.STATUS_UPDATING
    update_status.task_id = self.request.id
    update_status.save()

    try:
        character.update_character_details()
        character.update_corporation_history()

        update_status.status = CharacterUpdateStatus.STATUS_OKAY
        update_status.updated_on = timezone.now()
        update_status.expires_on = timezone.now() + timedelta(hours=24)
    except HTTPNotFound as ex:
        update_status.status = CharacterUpdateStatus.STATUS_ERROR
        logger.info("%s: %s", type(ex).__name__, ex)
        if ex.swagger_result["error"] == "Character has been deleted!":
            logger.debug("Character has been biomassed.")
            update_status.character.deleted = True
            update_status.character.save()
    except Exception as ex:
        update_status.status = CharacterUpdateStatus.STATUS_ERROR
        logger.error("%s: %s", type(ex).__name__, ex)

    update_status.task_id = None
    update_status.save()

    return bool(update_status.status == CharacterUpdateStatus.STATUS_OKAY)
