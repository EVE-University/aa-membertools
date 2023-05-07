# Standard Library
import ast
from typing import List, Optional

# Django
from django.apps import apps
from django.contrib.auth.models import User
from django.db import models, transaction
from django.db.models import Case, Q, When

# Alliance Auth
from allianceauth.eveonline.models import EveCorporationInfo
from allianceauth.services.hooks import get_extension_logger

logger = get_extension_logger(__name__)


class ApplicationFormManager(models.Manager):
    def get_forms_for_user(self, user: User) -> Optional[List[models.Model]]:
        if user.is_superuser:
            return self.all()

        groups = user.groups.all()
        is_auditor = Case(
            When(auditor_groups__in=groups, then=True),
            default=False,
            output_field=models.BooleanField(),
        )
        is_recruiter = Case(
            When(recruiter_groups__in=groups, then=True),
            default=False,
            output_field=models.BooleanField(),
        )
        is_manager = Case(
            When(manager_groups__in=groups, then=True),
            default=False,
            output_field=models.BooleanField(),
        )
        return (
            self.filter(
                Q(auditor_groups__in=groups)
                | Q(recruiter_groups__in=groups)
                | Q(manager_groups__in=groups)
            )
            .annotate(is_auditor=is_auditor)
            .annotate(is_recruiter=is_recruiter)
            .annotate(is_manager=is_manager)
        )

    def get_auditor_forms_for_user(self, user: User) -> Optional[List[models.Model]]:
        if user.is_superuser:
            return self.all()

        return self.filter(auditor_groups__in=user.groups.all())

    def get_recruiter_forms_for_user(self, user: User) -> Optional[List[models.Model]]:
        if user.is_superuser:
            return self.all()

        return self.filter(recruiter_groups__in=user.groups.all())

    def get_manager_forms_for_user(self, user: User) -> Optional[List[models.Model]]:
        if user.is_superuser:
            return self.all()

        return self.filter(manager_groups__in=user.groups.all())


class ApplicationManager(models.Manager):
    def recent_finished_apps_count_for_user(self, user: User) -> Optional[int]:
        """Returns recently finished application count for the user"""
        Application = apps.get_model("membertools", "Application")

        return Application.objects.filter(
            eve_character__character_ownership__user=user,
            status=Application.STATUS_PROCESSED,
            decision__in=[
                Application.DECISION_ACCEPT,
                Application.DECISION_REJECT,
                Application.DECISION_WITHDRAW,
            ],
        ).count()

    def new_application_count_for_admin_user(self, user: User) -> Optional[int]:
        """Returns number of New applications visible to the user."""
        Application = apps.get_model("membertools", "Application")
        ApplicationForm = apps.get_model("membertools", "ApplicationForm")

        base_query = self.filter(status=Application.STATUS_NEW)
        if user.is_superuser:
            return base_query.count()

        return base_query.filter(
            form__in=ApplicationForm.objects.get_recruiter_forms_for_user(user)
        ).count()

    def wait_application_count_for_admin_user(self, user: User) -> Optional[int]:
        """Returns number of Pending applications visible to the user."""
        Application = apps.get_model("membertools", "Application")
        ApplicationForm = apps.get_model("membertools", "ApplicationForm")

        base_query = self.filter(status=Application.STATUS_WAIT)
        if user.is_superuser:
            return base_query.count()

        return base_query.filter(
            form__in=ApplicationForm.objects.get_recruiter_forms_for_user(user)
        ).count()


class ApplicationActionManager(models.Manager):
    def create_action(
        self, application, action, action_by, action_on=None, override_by=None
    ):
        # Build args this way so we can exclude passing parameters that are None.
        # As None will override defaults like timezone.now for action_on
        kwargs = {
            "application": application,
            "action": action,
            "action_by": action_by,
        }

        if action_on is not None:
            kwargs["action_on"] = action_on
        if override_by is not None:
            kwargs["override_by"] = override_by

        return self.create(**kwargs)


class MemberManager(models.Manager):
    pass


class CharacterManager(models.Manager):
    def update_for_char(self, character, esi_details, last_modified=None, expires=None):
        description = esi_details.get("description", "")

        # ESI returns a python u string literal if the description contains a non-ascii character.
        # See: https://github.com/esi/esi-issues/issues/1265
        # The XML filtering provided by CCP is NOT extensive and it is easily possible to inject
        # arbitrary XML. This field should always be treated as unsafe without proper processing.

        if description and description.startswith("u'") and description.endswith("'"):
            try:
                description = ast.literal_eval(description)
            except SyntaxError:
                logger.warning(
                    "Invalid syntax from u-bug fix in description of %s [%s].",
                    character.eve_character.character_name,
                    character.eve_character.character_id,
                )
                description = ""

        try:
            corporation = EveCorporationInfo.objects.get(
                corporation_id=esi_details.get("corporation_id")
            )
        except EveCorporationInfo.DoesNotExist:
            corporation = EveCorporationInfo.objects.create_corporation(
                esi_details.get("corporation_id")
            )

        self.update_or_create(
            eve_character=character.eve_character,
            defaults={
                "corporation": corporation,
                "alliance": corporation.alliance,
                "birthday": esi_details.get("birthday"),
                "description": description,
                "security_status": esi_details.get("security_status"),
                "title": esi_details.get("title", ""),
            },
        )


class CharacterCorpHistoryManager(models.Manager):
    def update_char(self, character, history):
        corps = []
        for row in history:
            try:
                corporation = EveCorporationInfo.objects.update_corporation(
                    row.get("corporation_id")
                )
                logger.debug("Updated corp: %s [%s", corporation, corporation.alliance)
            except EveCorporationInfo.DoesNotExist:
                corporation = EveCorporationInfo.objects.create_corporation(
                    row.get("corporation_id")
                )
                logger.debug("Created corp: %s [%s", corporation, corporation.alliance)

            corps.append(
                self.model(
                    character=character,
                    record_id=row.get("record_id"),
                    corporation=corporation,
                    is_deleted=bool(row.get("is_deleted")),
                    start_date=row.get("start_date"),
                    end_date=corps[-1].start_date if len(corps) else None,
                )
            )

        if not len(corps):
            logger.info("%s: No corporation history?", character)

            return

        corps[-1].is_last = True

        with transaction.atomic():
            self.filter(character=character).delete()

            logger.info(
                "%s: Adding %s entries for corp history.", character, len(corps)
            )
            self.bulk_create(corps)
