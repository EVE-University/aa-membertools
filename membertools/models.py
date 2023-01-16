import unicodedata

from datetime import timedelta

from django.contrib.auth.models import User, Group
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.apps import apps
from django.db import models
from django.db.models import Q
from django.conf import settings
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.functional import cached_property
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _

from sortedm2m.fields import SortedManyToManyField

from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import (
    EveAllianceInfo,
    EveCharacter,
    EveCorporationInfo,
)

from esi.models import Token

from allianceauth.services.hooks import get_extension_logger

from .app_settings import MEMBERTOOLS_MAIN_CORP_ID

from .managers import (
    ApplicationFormManager,
    ApplicationManager,
    ApplicationActionManager,
    CharacterManager,
    CharacterCorpHistoryManager,
    MemberManager,
)
from .providers import EsiClientProvider

logger = get_extension_logger(__name__)
esi = EsiClientProvider()


class General(models.Model):
    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ("basic_access", "Can access the applicant areas"),
            ("admin_access", "Can access admin areas"),
            ("character_admin_access", "Can access the character list"),
            ("application_admin_access", "Can access the application list"),
            ("queue_admin_access", "Can access the queues"),
        )


class ApplicationQuestion(models.Model):
    title = models.CharField(max_length=254, verbose_name="Question")
    help_text = models.CharField(max_length=254, blank=True, null=True)
    multi_select = models.BooleanField(default=False)

    def __str__(self):
        return "Question: " + self.title


class ApplicationChoice(models.Model):
    question = models.ForeignKey(
        ApplicationQuestion, on_delete=models.CASCADE, related_name="choices"
    )
    choice_text = models.CharField(max_length=200, verbose_name="Choice")

    def __str__(self):
        return self.choice_text


def _get_app_title_none_id():
    res, _ = ApplicationTitle.objects.get_or_create(name="None", priority=0)

    return res.id


def _get_app_title_none():
    res, _ = ApplicationTitle.objects.get_or_create(name="None", priority=0)

    return res


class ApplicationTitle(models.Model):
    name = models.CharField(max_length=64)
    priority = models.SmallIntegerField(default=0)

    class Meta:
        verbose_name = _("Title")
        verbose_name_plural = _("Titles")
        ordering = ["priority"]

    def __str__(self):
        return str(self.name)

    def __ge__(self, x):
        return self.priority >= x.priority

    def __le__(self, x):
        return self.priority <= x.priority

    def __gt__(self, x):
        return self.priority > x.priority

    def __lt__(self, x):
        return self.priority < x.priority


class ApplicationForm(models.Model):
    questions = SortedManyToManyField(ApplicationQuestion, blank=True)
    corp = models.ForeignKey(
        EveCorporationInfo, on_delete=models.CASCADE, related_name="next_forms"
    )
    title = models.ForeignKey(
        ApplicationTitle, on_delete=models.PROTECT, blank=True, null=True
    )
    description = models.TextField(max_length=2048, blank=True, null=True)
    allow_awarded = models.ManyToManyField(
        ApplicationTitle, related_name="awarded", verbose_name="Allowed Awarded Titles"
    )
    allow_applied = models.ManyToManyField(
        ApplicationTitle, related_name="applied", verbose_name="Allowed Applied Titles"
    )
    auditor_groups = models.ManyToManyField(
        Group, related_name="next_form_auditor_groups", blank=True
    )
    recruiter_groups = models.ManyToManyField(
        Group, related_name="next_form_recruiter_groups", blank=True
    )
    manager_groups = models.ManyToManyField(
        Group, related_name="next_form_manager_groups", blank=True
    )
    pre_text = models.TextField(max_length=4096, blank=True, default="")
    post_text = models.TextField(max_length=4096, blank=True, default="")
    accept_template_subject = models.TextField(max_length=1000, default="")
    accept_template_body = models.TextField(max_length=10000, default="")
    reject_template_subject = models.TextField(max_length=1000, default="")
    reject_template_body = models.TextField(max_length=10000, default="")

    objects = ApplicationFormManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["corp", "title"], name="corp title unique apps"
            ),
        ]

    def is_user_auditor(self, user):
        if user.is_superuser:
            return True
        return self.auditor_groups.filter(
            authgroup__in=user.groups.values_list("pk").all()
        )

    def is_user_recruiter(self, user):
        if user.is_superuser:
            return True
        return self.recruiter_groups.filter(
            authgroup__in=user.groups.values_list("pk").all()
        )

    def is_user_manager(self, user):
        if user.is_superuser:
            return True
        return self.manager_groups.filter(
            authgroup__in=user.groups.values_list("pk").all()
        )

    def get_user_eligible_chars(self, user):
        logger.debug("get_user_eligible_chars(): User: %s Form: %s", user, self)
        try:
            main_char = user.profile.main_character
        except ObjectDoesNotExist:
            main_char = None

        if not main_char:
            logger.debug("User %s has no main character.", user)
            return []

        # TODO: Add settings param for this timedelta
        base_app_query = self.applications.filter(
            eve_character__character_ownership__user=user
        ).filter(
            Q(closed_on__isnull=False)
            & Q(closed_on__lte=timezone.now() + timedelta(minutes=5))
            | (
                ~Q(status=Application.DECISION_ACCEPT)
                & ~Q(status=Application.DECISION_REJECT)
                & ~Q(status=Application.DECISION_WITHDRAW)
            )
        )
        none_title = _get_app_title_none()

        owned_chars = [
            co.character for co in CharacterOwnership.objects.filter(user=user)
        ]

        try:
            main_detail = main_char.next_character
            try:
                main_applied = main_detail.applied_title
            except AttributeError:
                main_applied = none_title
        except ObjectDoesNotExist:
            main_detail = None
            main_applied = none_title

        try:
            member = main_char.next_character.member
            try:
                member_awarded = member.awarded_title
            except AttributeError:
                member_awarded = none_title
        except ObjectDoesNotExist:
            member = None
            member_awarded = none_title

        eligible_chars = []

        logger.debug("M: %s MA: %s", member, member_awarded)
        for eve_char in owned_chars:
            try:
                character = eve_char.next_character
                try:
                    char_applied = character.applied_title
                except ObjectDoesNotExist:
                    char_applied = none_title
            except ObjectDoesNotExist:
                character = None
                char_applied = none_title

            logger.debug("C: %s CD: %s CA: %s", eve_char, character, char_applied)

            # Check if we meet basic corp requirements
            if self.title and eve_char.corporation_id != self.corp.corporation_id:
                logger.debug("Isn't in corp for title form")
                continue
            elif not self.title and eve_char.corporation_id == self.corp.corporation_id:
                logger.debug("Is in corp for corp form")
                continue

            # Check if we meet title filters
            if member_awarded not in self.allow_awarded.all():
                logger.debug("Doesn't meet form allow_awarded")
                continue

            if char_applied not in self.allow_applied.all():
                logger.debug("Doesn't meet form allow_applied")
                continue

            # Recent app for this char
            query = base_app_query.filter(eve_character=eve_char)
            if query.count():
                logger.debug("Recent or active app(s) for char: %s", query.all())
                continue

            # Handle title form logic...
            if self.title:
                if eve_char != main_char:
                    if self.title > main_applied:
                        logger.debug(
                            "Alt cannot use title form for a higher title than main has applied"
                        )
                        continue
                    elif self.title == char_applied:
                        logger.debug("Alt already has title")
                        continue
                else:
                    if self.title <= member_awarded:
                        logger.debug("Not showing already passed/earned title for main")
                        continue

            eligible_chars.append(eve_char)

        return eligible_chars

    def user_has_eligible_chars(self, user):
        return bool(self.get_user_eligible_chars(user))

    def __str__(self):
        return str(self.corp) + (f": {self.title} " + _("Title") if self.title else "")


class Application(models.Model):
    STATUS_NEW = 1
    STATUS_REVIEW = 2
    STATUS_WAIT = 3
    STATUS_PROCESSED = 4
    STATUS_CLOSED = 5
    STATUS_CHOICES = (
        (STATUS_NEW, _("New")),
        (STATUS_REVIEW, _("Under Review")),
        (STATUS_WAIT, _("Wait")),
        (STATUS_PROCESSED, _("Processed")),
        (STATUS_CLOSED, _("Closed")),
    )

    STATUS_MESSAGE = {
        STATUS_NEW: _(
            "Your application has been submitted and is in the queue for review."
        ),
        STATUS_REVIEW: _("Your application is currently being reviewed."),
        STATUS_WAIT: _(
            "Your application has been reviewed and more information may be required. Check your EVE Mail for more information."
        ),
        STATUS_PROCESSED: _(
            "Your application has been processed. Check your EVE Mail for more information."
        ),
        STATUS_CLOSED: _("This application is closed and has been archived."),
    }

    # No decision has been made
    DECISION_PENDING = 0
    # Application accepted
    DECISION_ACCEPT = 1
    # Application rejected
    DECISION_REJECT = 2
    # Application was withdrawn
    DECISION_WITHDRAW = 3

    DECISION_CHOICES = (
        (DECISION_PENDING, _("Pending")),
        (DECISION_ACCEPT, _("Accept")),
        (DECISION_REJECT, _("Reject")),
        (DECISION_WITHDRAW, _("Withdrawn")),
    )

    DECISION_MESSAGE = {
        DECISION_PENDING: "Awaiting decision of your application.",
        DECISION_ACCEPT: "Your application has been accepted! Check your EVE Mail for more information.",
        DECISION_REJECT: "Your application was rejected. Check your EVE Mail for more information.",
        DECISION_WITHDRAW: "Your application was withdrawn.",
    }
    form = models.ForeignKey(
        ApplicationForm, on_delete=models.CASCADE, related_name="applications"
    )
    character = models.ForeignKey(
        "Character",
        on_delete=models.CASCADE,
        related_name="applications",
    )
    eve_character = models.ForeignKey(
        EveCharacter,
        on_delete=models.CASCADE,
        related_name="next_applications",
    )
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=STATUS_NEW)
    status_on = models.DateTimeField(auto_now_add=True)
    last_status = models.SmallIntegerField(choices=STATUS_CHOICES, default=STATUS_NEW)
    decision = models.SmallIntegerField(
        choices=DECISION_CHOICES, default=DECISION_PENDING
    )
    decision_by = models.ForeignKey(
        EveCharacter, on_delete=models.CASCADE, blank=True, null=True, related_name="+"
    )
    decision_on = models.DateTimeField(blank=True, null=True)
    reviewer = models.ForeignKey(
        EveCharacter,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="+",
    )
    submitted_on = models.DateTimeField(auto_now_add=True)
    closed_on = models.DateTimeField(blank=True, null=True)

    objects = ApplicationManager()

    def clean(self):
        errors = {}

        # Status
        if (
            self.status not in [Application.STATUS_PROCESSED, Application.STATUS_CLOSED]
            and self.decision != Application.DECISION_PENDING
        ):
            errors["status"] = ValidationError(
                f"Status {self.get_status_display()} is not valid when Decision isn't Pending.",
                code="invalid",
            )

        if (
            self.status
            in [
                Application.STATUS_REVIEW,
                Application.STATUS_PROCESSED,
                Application.STATUS_CLOSED,
            ]
            and self.reviewer is None
        ):
            errors["status"] = ValidationError(
                f"Status must not be {self.get_status_display()} without a reviewer.",
                code="invalid",
            )

        if (
            self.status not in [Application.STATUS_PROCESSED, Application.STATUS_CLOSED]
            and self.decision != Application.DECISION_PENDING
        ):
            errors["status"] = ValidationError(
                f"Status cannot be {self.get_status_display()} without a Decision.",
                code="invalid",
            )

        # Last Status
        if self.last_status in [
            Application.STATUS_REVIEW,
            Application.STATUS_PROCESSED,
            Application.STATUS_CLOSED,
        ]:
            errors["last_status"] = ValidationError(
                f"Last status cannot be {self.get_status_display()}.", code="invalid"
            )

        # Decision
        if self.decision == Application.DECISION_PENDING and self.status in [
            Application.STATUS_PROCESSED,
            Application.STATUS_CLOSED,
        ]:
            errors["decision"] = ValidationError(
                f"Decision cannot be Pending when Status is {self.get_status_display()}.",
                code="invalid",
            )
        elif self.decision != Application.DECISION_PENDING and self.status not in [
            Application.STATUS_PROCESSED,
            Application.STATUS_CLOSED,
        ]:
            errors["decision"] = ValidationError(
                "Decision must be Pending when Status isn't Processed/Closed.",
                code="invalid",
            )

        # Decision By
        if self.decision_by is not None and self.status not in [
            Application.STATUS_PROCESSED,
            Application.STATUS_CLOSED,
        ]:
            errors["decision_by"] = ValidationError(
                "Decision by must be empty when Status isn't Processed/Closed.",
                code="invalid",
            )
        elif self.decision_by is None and self.decision != Application.DECISION_PENDING:
            errors["decision_by"] = ValidationError(
                "Decision by may not be empty when Decision isn't Pending.",
                code="invalid",
            )

        # Reviewer
        if self.reviewer is not None and self.status == Application.STATUS_NEW:
            errors["reviewer"] = ValidationError(
                "Reviewer cannot be set if Status is New", code="invalid"
            )
        elif self.reviewer is None and self.decision != Application.DECISION_PENDING:
            errors["reviewer"] = ValidationError(
                "Reviewer cannot be empty if Decision is not Pending", code="invalid"
            )

        if len(errors):
            raise ValidationError(errors)

    # Handle some automated field changes
    def save(self, *args, **kwargs):
        if self.pk:
            old_instance = Application.objects.get(pk=self.pk)
        else:
            old_instance = None

        # Empty read only decision on if status isn't PROCESSED or CLOSED
        if self.status not in [Application.STATUS_PROCESSED, Application.STATUS_CLOSED]:
            self.decision_on = None

        # Last status must always be NEW when Status is NEW
        if self.status == Application.STATUS_NEW:
            self.last_status = Application.STATUS_NEW

        if old_instance:
            if old_instance.status != self.status:
                self.status_on = timezone.now()

                if (
                    old_instance.status != Application.STATUS_CLOSED
                    and self.status == Application.STATUS_CLOSED
                ):
                    self.closed_on = timezone.now()
                elif (
                    old_instance.status == Application.STATUS_CLOSED
                    and self.status != Application.STATUS_CLOSED
                ):
                    self.closed_on = None

            if (
                old_instance.decision == Application.DECISION_PENDING
                and self.decision != Application.DECISION_PENDING
            ):
                self.decision_on = timezone.now()
            elif self.decision == Application.DECISION_PENDING:
                self.decision_on = None

        super(Application, self).save(*args, **kwargs)

    def __str__(self):
        formatted = date_format(
            self.submitted_on, format="SHORT_DATE_FORMAT", use_l10n=True
        )
        if self.form.title:
            name = self.form.title
        else:
            name = self.form.corp
        return f"{name} ({formatted})"

    class Meta:
        permissions = (
            ("review_application", "Can review applications"),
            ("reject_application", "Can reject applications"),
            ("manage_application", "Can override actions on applications"),
        )

    @cached_property
    def character_ownership(self):
        try:
            return self.eve_character.character_ownership
        except ObjectDoesNotExist:
            return None

    @cached_property
    def user(self):
        try:
            return self.eve_character.character_ownership.user
        except AttributeError:
            return None

    @cached_property
    def main_character(self):
        try:
            return self.eve_character.character_ownership.user.profile.main_character
        except AttributeError:
            return None

    @cached_property
    def member(self):
        try:
            return self.character.member
        except AttributeError:
            return None

    @cached_property
    def characters(self):
        return [o.character for o in self.user.character_ownerships.all()]

    @cached_property
    def reviewer_str(self):
        return str(self.reviewer)

    def get_status_message(self):
        return self.STATUS_MESSAGE[self.status]

    def get_decision_message(self):
        return self.DECISION_MESSAGE[self.decision]


class ApplicationResponse(models.Model):
    question = models.ForeignKey(ApplicationQuestion, on_delete=models.CASCADE)
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="responses"
    )
    answer = models.TextField()

    def __str__(self):
        return str(self.application) + " Answer To " + str(self.question)

    class Meta:
        unique_together = ("question", "application")


class ApplicationAction(models.Model):
    REVIEW = 1
    ACCEPT = 2
    REJECT = 3
    WAIT = 4
    RELEASE = 5
    CLOSE = 6
    ACTION_CHOICES = (
        (REVIEW, _("Start Review")),
        (ACCEPT, _("Accept")),
        (REJECT, _("Reject")),
        (WAIT, _("Wait")),
        (RELEASE, _("Release")),
        (CLOSE, _("Close")),
    )

    ACTION_MESSAGE = {
        REVIEW: _("Start reviewing application. Claiming ownership of application."),
        ACCEPT: _("Accept application."),
        REJECT: _("Reject application."),
        WAIT: _("Waiting for feedback/response."),
        RELEASE: _("Release ownership of application and return it to queue."),
        CLOSE: _("Close application and remove temporary membership state."),
    }

    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="actions"
    )
    action = models.SmallIntegerField(choices=ACTION_CHOICES)
    action_on = models.DateTimeField(auto_now_add=True)
    action_by = models.ForeignKey(
        EveCharacter,
        on_delete=models.CASCADE,
        related_name="+",
    )
    override_by = models.ForeignKey(
        EveCharacter,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="+",
    )

    objects = ApplicationActionManager()

    class Meta:
        ordering = ["-action_on"]

    def __str__(self):
        return "{} - {}".format(self.application, self.get_action_display())


class Comment(models.Model):
    member = models.ForeignKey(
        "Member",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="comments",
    )
    character = models.ForeignKey(
        "Character",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="comments",
    )
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="comments",
    )
    poster = models.ForeignKey(
        EveCharacter,
        on_delete=models.CASCADE,
        related_name="+",
    )
    text = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.poster) + " comment on " + str(self.application)


class Member(models.Model):
    awarded_title = models.ForeignKey(
        ApplicationTitle,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        default=_get_app_title_none_id,
    )
    first_joined = models.DateTimeField(blank=True, null=True)
    last_joined = models.DateTimeField(blank=True, null=True)
    first_main_character = models.ForeignKey(
        EveCharacter,
        on_delete=models.CASCADE,
        related_name="+",
        null=True,
    )
    main_character = models.ForeignKey(
        EveCharacter,
        on_delete=models.CASCADE,
        related_name="next_member",
        null=True,
    )
    characters = models.ManyToManyField(EveCharacter, through="CharacterLink")

    objects = MemberManager()

    class Meta:
        verbose_name = _("Member")
        verbose_name_plural = _("Members")
        ordering = ["id"]

    @cached_property
    def character_ownership(self):
        try:
            return self.main_character.character_ownership
        except ObjectDoesNotExist:
            return None

    @cached_property
    def user(self):
        try:
            return self.main_character.character_ownership.user
        except AttributeError:
            return None

    @cached_property
    def characters(self):
        return [
            owner.character
            for owner in self.character_ownership.user.character_ownerships.select_related(
                "character"
            ).order_by(
                "character__corporation_id", "character__character_name"
            )
        ]

    def update_joined_dates(self, forced=False):
        if not forced and self.first_joined and self.last_joined:
            return False

        history = esi.client.Character.get_characters_character_id_corporationhistory(
            character_id=self.character.character_id
        )

        history.reverse()

        logger.debug(history)

        member_corp_id = MEMBERTOOLS_MAIN_CORP_ID
        first_join = False
        last_join = False

        for corp in history:
            if corp["corporation_id"] == member_corp_id:
                if not first_join:
                    first_join = corp["start_date"]

                last_join = corp["start_date"]

        logger.debug("F: %s L: %s", first_join, last_join)

        self.first_joined = first_join
        self.last_joined = last_join
        self.save()

        logger.debug("MF: %s ML: %s", self.first_joined, self.last_joined)

        return True

    def __str__(self):
        return (
            str(self.main_character.character_name)
            if self.main_character
            else f"Unknown Member ({self.id})"
        )


class Character(models.Model):
    eve_character = models.OneToOneField(
        EveCharacter,
        on_delete=models.CASCADE,
        related_name="next_character",
    )
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="character",
        blank=True,
        null=True,
    )
    applied_title = models.ForeignKey(
        ApplicationTitle,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        default=_get_app_title_none_id,
    )
    birthday = models.DateTimeField(null=True)
    corporation = models.ForeignKey(
        EveCorporationInfo, on_delete=models.PROTECT, null=True, related_name="+"
    )
    alliance = models.ForeignKey(
        EveAllianceInfo, on_delete=models.PROTECT, null=True, related_name="+"
    )
    description = models.TextField(null=True)
    security_status = models.FloatField(default=None, null=True)
    title = models.TextField(null=True)
    deleted = models.BooleanField(default=False)

    objects = CharacterManager()

    class Meta:
        verbose_name = _("Character")
        verbose_name_plural = _("Characters")
        ordering = ["eve_character__character_name"]

    @cached_property
    def character_name(self):
        return self.eve_character.character_name

    @cached_property
    def character_ownership(self):
        try:
            return self.eve_character.character_ownership
        except ObjectDoesNotExist:
            return None

    @cached_property
    def user(self):
        try:
            return self.eve_character.character_ownership.user
        except AttributeError:
            return None

    @cached_property
    def main_character(self):
        try:
            return self.eve_character.character_ownership.user.profile.main_character
        except AttributeError:
            return None

    @cached_property
    def applications(self):
        return Application.objects.filter(user=self.user).order_by("pk")

    @cached_property
    def description_text(self):
        desc = self.description.strip()
        if desc == "":
            return None

        return strip_tags(unicodedata.normalize("NFKC", desc).replace("<br>", "\n"))

    @staticmethod
    def _get_ma_character(character):
        try:
            MACharacter = apps.get_model("memberaudit", "Character")
            ma_character = MACharacter.objects.get(eve_character=character)
        except LookupError:
            return None
        except MACharacter.DoesNotExist:
            return None

        return ma_character

    @cached_property
    def memberaudit_character(self):
        return Character._get_ma_character(self.eve_character)

    @cached_property
    def location(self):
        character = Character._get_ma_character(self.eve_character)

        if not character:
            return None

        return character.location.location

    @cached_property
    def skillpoints_total(self):
        character = Character._get_ma_character(self.eve_character)

        if not character:
            return None

        return character.skillpoints.total

    @cached_property
    def skillpoints_unallocated(self):
        character = Character._get_ma_character(self.eve_character)

        if not character:
            return None

        return character.skillpoints.unallocated

    @cached_property
    def wallet_balance(self):
        character = Character._get_ma_character(self.eve_character)

        if not character:
            return None

        return character.wallet_balance.total

    @cached_property
    def wallet_balance(self):
        character = Character._get_ma_character(self.eve_character)

        if not character:
            return None

        return character.wallet_balance.total

    @cached_property
    def online_last_login(self):
        character = Character._get_ma_character(self.eve_character)

        if not character:
            return None

        return character.online_status.last_login

    def __str__(self):
        return str(self.eve_character.character_name)

    def update_character_details(self, force=False):
        logger.debug("update_character_details(): %s", self)
        if (
            not force
            and self.update_status
            and self.update_status.expires_on
            and self.update_status.expires_on > timezone.now()
        ):
            return False
        details = esi.client.Character.get_characters_character_id(
            character_id=self.eve_character.character_id
        ).results()

        logger.debug("Updating details for %s.", details.get("name"))
        Character.objects.update_for_char(self, details)
        return True

    def update_corporation_history(self, force=False):
        logger.debug("update_corporation_history(): %s", self)
        if (
            not force
            and self.update_status
            and self.update_status.expires_on
            and self.update_status.expires_on > timezone.now()
        ):
            return False
        history = esi.client.Character.get_characters_character_id_corporationhistory(
            character_id=self.eve_character.character_id
        ).results()

        self.corporation_history.update_for_char(self, history)
        return True


class CharacterCorpHistory(models.Model):
    character = models.ForeignKey(
        Character, on_delete=models.CASCADE, related_name="corporation_history"
    )
    record_id = models.PositiveIntegerField()
    corporation = models.ForeignKey(
        EveCorporationInfo, on_delete=models.CASCADE, related_name="+"
    )
    is_deleted = models.BooleanField(default=False)
    is_last = models.BooleanField(default=False)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True)

    objects = CharacterCorpHistoryManager()

    class Meta:
        indexes = [
            models.Index(fields=["character"]),
            models.Index(fields=["record_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["character", "record_id"], name="unique_character_record"
            )
        ]

    def __str__(self) -> str:
        return f"{self.character}-{self.record_id}"


class CharacterUpdateStatus(models.Model):
    STATUS_OKAY = 1
    STATUS_ERROR = 2
    STATUS_UPDATING = 3
    STATUS_CHOICES = (
        (STATUS_OKAY, _("Okay")),
        (STATUS_ERROR, _("Error")),
        (STATUS_UPDATING, _("Updating")),
    )

    character = models.OneToOneField(
        Character, on_delete=models.CASCADE, related_name="update_status"
    )
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES)
    updated_on = models.DateTimeField(null=True, default=timezone.now)
    expires_on = models.DateTimeField(null=True)
    task_id = models.UUIDField(null=True)

    class Meta:
        indexes = [
            models.Index(fields=["expires_on"]),
        ]

    def __str__(self):
        return f"{self.character} [{self.updated_on}]: {self.get_status_display()}"


class CharacterLink(models.Model):
    SOURCE_ESI = 1
    SOURCE_PREVIOUS_ESI = 2
    SOURCE_MANUAL = 3
    SOURCE_CHOICES = (
        (SOURCE_ESI, _("ESI Verified")),
        (SOURCE_PREVIOUS_ESI, _("Previous ESI")),
        (SOURCE_MANUAL, _("Manually Added")),
    )
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name="+")
    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name="character_links"
    )
    source = models.SmallIntegerField(choices=SOURCE_CHOICES)
    linked_on = models.DateTimeField()
    linked_by = models.ForeignKey(
        EveCharacter, on_delete=models.CASCADE, related_name="+"
    )
    esi_token = models.ForeignKey(
        Token, on_delete=models.SET_NULL, blank=True, null=True
    )
    reason = models.TextField(max_length=1024)
