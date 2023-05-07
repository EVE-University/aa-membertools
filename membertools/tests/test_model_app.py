# Standard Library
import datetime
from unittest.mock import patch

# Django
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

# Alliance Auth
from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
from allianceauth.tests.auth_utils import AuthUtils

from ..models import (
    Application,
    ApplicationForm,
    ApplicationQuestion,
    ApplicationTitle,
    Character,
    Member,
)


class TestModelApp(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.corp = EveCorporationInfo.objects.create(
            corporation_id=10,
            corporation_name="Join Me",
            corporation_ticker="JOIN",
            member_count=20,
        )
        cls.corp_app_form = ApplicationForm.objects.create(corp=cls.corp)
        cls.corp_app_form.questions.add(
            ApplicationQuestion.objects.create(
                title="Text Question",
                help_text="A text question",
            )
        )

        cls.title = ApplicationTitle.objects.create(name="A Title", priority=1)
        cls.title_app_form = ApplicationForm.objects.create(
            corp=cls.corp,
            title=cls.title,
        )
        cls.title_app_form.questions.add(
            ApplicationQuestion.objects.create(
                title="Text Question",
                help_text="A text question",
            )
        )

        # Make some users/mains
        AuthUtils.disconnect_signals()

        cls.officer = AuthUtils.create_user("Recruitment_Officer")

        cls.officer_eve_char = EveCharacter.objects.create(
            character_id=10,
            character_name="Recruitment Officer",
            corporation_id=cls.corp.corporation_id,
            corporation_name=cls.corp.corporation_name,
            corporation_ticker=cls.corp.corporation_ticker,
        )

        cls.officer.profile.main_character = cls.officer_eve_char
        cls.officer.profile.save()

        CharacterOwnership.objects.create(
            user=cls.officer,
            character=cls.officer_eve_char,
            owner_hash="10",
        )

        cls.applicant = AuthUtils.create_user("Applicant_1")

        cls.applicant_eve_char = EveCharacter.objects.create(
            character_id=1,
            character_name="Applicant 1",
            corporation_id=1,
            corporation_name="Corp",
            corporation_ticker="CORP",
        )

        cls.applicant.profile.main_character = cls.applicant_eve_char
        cls.applicant.profile.save()

        CharacterOwnership.objects.create(
            user=cls.applicant,
            character=cls.applicant_eve_char,
            owner_hash="1",
        )

        cls.member = AuthUtils.create_user("Member_1")

        cls.member_eve_char = EveCharacter.objects.create(
            character_id=2,
            character_name="Member 1",
            corporation_id=cls.corp.corporation_id,
            corporation_name=cls.corp.corporation_name,
            corporation_ticker=cls.corp.corporation_ticker,
        )

        cls.member.profile.main_character = cls.member_eve_char
        cls.member.profile.save()

        CharacterOwnership.objects.create(
            user=cls.member,
            character=cls.member_eve_char,
            owner_hash="2",
        )

        AuthUtils.connect_signals()

        return super().setUpTestData()

    # Clean Status
    def test_clean_new_status_non_pending_decision_raises(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )
        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            reviewer=self.officer_eve_char,
            decision_by=self.officer_eve_char,
            status=Application.STATUS_NEW,
            decision=Application.DECISION_ACCEPT,
        )

        with self.assertRaises(ValidationError) as context:
            app.clean()

        self.assertEqual(len(context.exception.error_dict), 4)
        self.assertCountEqual(
            context.exception.error_dict.keys(),
            ["status", "decision", "decision_by", "reviewer"],
        )

    def test_clean_wait_status_non_pending_decision_raises(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )
        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            reviewer=self.officer_eve_char,
            decision_by=self.officer_eve_char,
            status=Application.STATUS_WAIT,
            decision=Application.DECISION_REJECT,
        )

        with self.assertRaises(ValidationError) as context:
            app.clean()

        print(context.exception.error_dict.keys())
        print(context.exception.message_dict.items())
        self.assertEqual(len(context.exception.message_dict), 3)
        self.assertCountEqual(
            context.exception.error_dict.keys(),
            ["status", "decision", "decision_by"],
        )

    def test_clean_review_status_non_pending_decision_raises(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )
        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            reviewer=self.officer_eve_char,
            decision_by=self.officer_eve_char,
            status=Application.STATUS_REVIEW,
            decision=Application.DECISION_WITHDRAW,
        )

        with self.assertRaises(ValidationError) as context:
            app.clean()

        self.assertEqual(len(context.exception.message_dict), 3)
        self.assertCountEqual(
            context.exception.error_dict.keys(),
            ["status", "decision", "decision_by"],
        )

    def test_clean_new_status_pending_decision_is_valid(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )
        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_NEW,
            decision=Application.DECISION_PENDING,
        )

        app.clean()

    def test_clean_wait_status_pending_decision_is_valid(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )
        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_WAIT,
            decision=Application.DECISION_PENDING,
        )

        app.clean()

    def test_clean_review_status_pending_decision_with_reviewer_is_valid(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )
        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_REVIEW,
            decision=Application.DECISION_PENDING,
            reviewer=self.officer_eve_char,
        )

        app.clean()

    def test_clean_review_status_pending_decision_without_reviewer_raises(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )
        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_REVIEW,
            decision=Application.DECISION_PENDING,
        )

        with self.assertRaises(ValidationError) as context:
            app.clean()

        self.assertEqual(len(context.exception.message_dict), 1)
        self.assertEqual(
            context.exception.message_dict["status"][0],
            "Status must not be Under Review without a reviewer.",
        )

    # Clean Last Status
    def test_clean_last_status_review_raises(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )
        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_WAIT,
            decision=Application.DECISION_PENDING,
            last_status=Application.STATUS_REVIEW,
        )

        with self.assertRaises(ValidationError) as context:
            app.clean()

        self.assertEqual(len(context.exception.message_dict), 1)
        self.assertEqual(
            context.exception.message_dict["last_status"][0],
            "Last status cannot be Under Review.",
        )

    def test_clean_last_status_processed_raises(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )
        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_WAIT,
            decision=Application.DECISION_PENDING,
            last_status=Application.STATUS_PROCESSED,
        )

        with self.assertRaises(ValidationError) as context:
            app.clean()

        self.assertEqual(len(context.exception.message_dict), 1)
        self.assertEqual(
            context.exception.message_dict["last_status"][0],
            "Last status cannot be Processed.",
        )

    def test_clean_last_status_closed_raises(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )
        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_WAIT,
            decision=Application.DECISION_PENDING,
            last_status=Application.STATUS_CLOSED,
        )

        with self.assertRaises(ValidationError) as context:
            app.clean()

        self.assertEqual(len(context.exception.message_dict), 1)
        self.assertEqual(
            context.exception.message_dict["last_status"][0],
            "Last status cannot be Closed.",
        )

    def test_clean_last_status_new_is_valid(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )
        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_REVIEW,
            decision=Application.DECISION_PENDING,
            reviewer=self.officer_eve_char,
            last_status=Application.STATUS_NEW,
        )

        app.clean()

    def test_clean_last_status_wait_is_valid(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )
        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_REVIEW,
            decision=Application.DECISION_PENDING,
            reviewer=self.officer_eve_char,
            last_status=Application.STATUS_WAIT,
        )

        app.clean()

    # Clean Decision
    def test_clean_decision_pending_status_processed_raises(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )
        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            reviewer=self.officer_eve_char,
            decision_by=self.officer_eve_char,
            status=Application.STATUS_PROCESSED,
            decision=Application.DECISION_PENDING,
        )

        with self.assertRaises(ValidationError) as context:
            app.clean()

        self.assertEqual(len(context.exception.error_dict), 1)
        self.assertCountEqual(context.exception.error_dict, ["decision"])

    def test_clean_decision_pending_status_closed_raises(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )
        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            reviewer=self.officer_eve_char,
            decision_by=self.officer_eve_char,
            status=Application.STATUS_CLOSED,
            decision=Application.DECISION_PENDING,
        )

        with self.assertRaises(ValidationError) as context:
            app.clean()

        self.assertEqual(len(context.exception.error_dict), 1)
        self.assertCountEqual(context.exception.error_dict, ["decision"])

    def test_clean_decision_by_officer_status_processed_is_valid(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )
        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            reviewer=self.officer_eve_char,
            status=Application.STATUS_CLOSED,
            decision=Application.DECISION_ACCEPT,
            decision_by=self.officer_eve_char,
        )

        app.clean()

    def test_clean_decision_by_officer_status_closed_is_valid(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )
        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            reviewer=self.officer_eve_char,
            status=Application.STATUS_CLOSED,
            decision=Application.DECISION_REJECT,
            decision_by=self.officer_eve_char,
        )

        app.clean()

    def test_clean_decision_by_none_status_processed_raises(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )
        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            reviewer=self.officer_eve_char,
            status=Application.STATUS_PROCESSED,
            decision=Application.DECISION_ACCEPT,
            decision_by=None,
        )

        with self.assertRaises(ValidationError) as context:
            app.clean()

        self.assertEqual(len(context.exception.error_dict), 1)
        self.assertCountEqual(context.exception.error_dict, ["decision_by"])

    def test_clean_decision_by_none_status_closed_raises(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )
        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            reviewer=self.officer_eve_char,
            status=Application.STATUS_CLOSED,
            decision=Application.DECISION_REJECT,
            decision_by=None,
        )

        with self.assertRaises(ValidationError) as context:
            app.clean()

        self.assertEqual(len(context.exception.error_dict), 1)
        self.assertCountEqual(context.exception.error_dict, ["decision_by"])

    def test_clean_reviewer_none_status_new_is_valid(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )
        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_NEW,
            decision=Application.DECISION_PENDING,
            reviewer=None,
        )

        app.clean()

    def test_clean_reviewer_officer_status_new_raises(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )
        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_NEW,
            decision=Application.DECISION_PENDING,
            reviewer=self.officer_eve_char,
        )

        with self.assertRaises(ValidationError) as context:
            app.clean()

        self.assertEqual(len(context.exception.error_dict), 1)
        self.assertCountEqual(context.exception.error_dict, ["reviewer"])

    def test_clean_reviewer_none_decision_non_pending_raises(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )
        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_PROCESSED,
            decision=Application.DECISION_REJECT,
            decision_by=self.officer_eve_char,
            reviewer=None,
        )

        with self.assertRaises(ValidationError) as context:
            app.clean()

        self.assertEqual(len(context.exception.error_dict), 2)
        self.assertCountEqual(context.exception.error_dict, ["reviewer", "status"])

    def test_save_status_new_decision_on_must_be_none(self):
        test_datetime = datetime.datetime(2020, 1, 1, 1, 0, 0, 0, timezone.utc)
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )
        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_NEW,
            decision=Application.DECISION_PENDING,
            decision_on=test_datetime,
        )

        app.save()

        self.assertEqual(app.decision_on, None)

    def test_save_status_new_last_status_must_be_new(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )
        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_NEW,
            decision=Application.DECISION_PENDING,
            last_status=Application.STATUS_WAIT,
        )

        app.save()

        self.assertEqual(app.last_status, Application.STATUS_NEW)

    @patch("membertools.models.timezone.now")
    def test_save_status_change_updates_status_on(self, timezone_now_mock):
        test_datetime = datetime.datetime(2020, 1, 1, 1, 0, 0, 0, datetime.timezone.utc)
        test_datetime_2 = datetime.datetime(
            2020, 1, 2, 1, 0, 0, 0, datetime.timezone.utc
        )

        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        # The reference to timezone.now in object creation via default=timezone.now appears to already exist
        # here. Causing the mocked version to not called on create, but is called during save. So we define the
        # status_on datetime we want during creation.
        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_NEW,
            status_on=test_datetime,
            decision=Application.DECISION_PENDING,
        )

        app.save()

        self.assertEqual(app.status_on, test_datetime)

        timezone_now_mock.return_value = test_datetime_2

        app.status = Application.STATUS_WAIT
        app.save()

        timezone_now_mock.assert_called_once()
        self.assertEqual(app.status_on, test_datetime_2)

    def test_save_status_change_from_closed_unsets_closed_on(self):
        test_datetime = datetime.datetime(2020, 1, 1, 1, 0, 0, 0, datetime.timezone.utc)

        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_CLOSED,
            decision=Application.DECISION_ACCEPT,
            decision_by=self.officer_eve_char,
            reviewer=self.officer_eve_char,
            closed_on=test_datetime,
        )

        app.save()

        self.assertEqual(app.closed_on, test_datetime)

        app.status = Application.STATUS_WAIT
        app.save()

        self.assertEqual(app.closed_on, None)

    @patch("membertools.models.timezone.now")
    def test_save_status_change_to_closed_sets_closed_on(self, timezone_now_mock):
        test_datetime = datetime.datetime(2020, 1, 1, 1, 0, 0, 0, datetime.timezone.utc)

        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_PROCESSED,
            decision=Application.DECISION_ACCEPT,
            decision_by=self.officer_eve_char,
            decision_on=test_datetime,
            reviewer=self.officer_eve_char,
        )

        self.assertEqual(app.closed_on, None)

        timezone_now_mock.return_value = test_datetime

        app.status = Application.STATUS_CLOSED

        app.save()

        # This should have been called twice for status_on change and closed_on change.
        timezone_now_mock.assert_called()
        self.assertEqual(app.closed_on, test_datetime)

    def test_str_corp_app(self):
        test_datetime = datetime.datetime(2020, 1, 1, 1, 0, 0, 0, datetime.timezone.utc)
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_NEW,
            decision=Application.DECISION_PENDING,
            submitted_on=test_datetime,
        )

        self.assertEqual(str(app), "Join Me (01/01/2020)")

    def test_str_title_app(self):
        test_datetime = datetime.datetime(2020, 1, 1, 1, 0, 0, 0, datetime.timezone.utc)
        char = Character.objects.create(
            eve_character=self.member_eve_char,
            member=None,
        )

        app = Application.objects.create(
            form=self.title_app_form,
            character=char,
            eve_character=self.member_eve_char,
            status=Application.STATUS_NEW,
            decision=Application.DECISION_PENDING,
            submitted_on=test_datetime,
        )

        self.assertEqual(str(app), "A Title (01/01/2020)")

    def test_char_ownership_with_owned_char(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_NEW,
            decision=Application.DECISION_PENDING,
        )

        self.assertNotEqual(app.character_ownership, None)
        self.assertEqual(
            app.character_ownership, self.applicant_eve_char.character_ownership
        )

    def test_char_ownership_with_unowned_char(self):
        eve_char = EveCharacter.objects.create(
            character_id=3,
            character_name="Applicant 3",
            corporation_id=1,
            corporation_name="Corp",
            corporation_ticker="CORP",
        )

        char = Character.objects.create(
            eve_character=eve_char,
            member=None,
        )

        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=eve_char,
            status=Application.STATUS_NEW,
            decision=Application.DECISION_PENDING,
        )

        self.assertEqual(app.character_ownership, None)

    def test_user_with_owned_char(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_NEW,
            decision=Application.DECISION_PENDING,
        )

        self.assertNotEqual(app.user, None)
        self.assertEqual(app.user, self.applicant_eve_char.character_ownership.user)

    def test_user_with_unowned_char(self):
        eve_char = EveCharacter.objects.create(
            character_id=3,
            character_name="Applicant 3",
            corporation_id=1,
            corporation_name="Corp",
            corporation_ticker="CORP",
        )

        char = Character.objects.create(
            eve_character=eve_char,
            member=None,
        )

        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=eve_char,
            status=Application.STATUS_NEW,
            decision=Application.DECISION_PENDING,
        )

        self.assertEqual(app.user, None)

    def test_main_char_with_main_char(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_NEW,
            decision=Application.DECISION_PENDING,
        )

        self.assertNotEqual(app.main_character, None)
        self.assertEqual(
            app.main_character,
            self.applicant_eve_char.character_ownership.user.profile.main_character,
        )

    def test_main_char_without_main_char(self):
        eve_char = EveCharacter.objects.create(
            character_id=3,
            character_name="Applicant 3",
            corporation_id=1,
            corporation_name="Corp",
            corporation_ticker="CORP",
        )

        char = Character.objects.create(
            eve_character=eve_char,
            member=None,
        )

        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=eve_char,
            status=Application.STATUS_NEW,
            decision=Application.DECISION_PENDING,
        )

        self.assertEqual(app.main_character, None)

    def test_member_with_member(self):
        member = Member.objects.create(
            main_character=self.applicant_eve_char,
            first_main_character=self.applicant_eve_char,
        )
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=member,
        )

        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_NEW,
            decision=Application.DECISION_PENDING,
        )

        self.assertNotEqual(app.member, None)
        self.assertEqual(app.member, member)

    def test_member_with_non_member(self):
        eve_char = EveCharacter.objects.create(
            character_id=3,
            character_name="Applicant 3",
            corporation_id=1,
            corporation_name="Corp",
            corporation_ticker="CORP",
        )

        char = Character.objects.create(
            eve_character=eve_char,
            member=None,
        )

        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=eve_char,
            status=Application.STATUS_NEW,
            decision=Application.DECISION_PENDING,
        )

        self.assertEqual(app.member, None)

    def test_characters_with_single_char(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_NEW,
            decision=Application.DECISION_PENDING,
        )

        self.assertEqual(app.characters, [self.applicant_eve_char])

    def test_characters_with_multi_char(self):
        eve_char = EveCharacter.objects.create(
            character_id=3,
            character_name="Applicant 3",
            corporation_id=1,
            corporation_name="Corp",
            corporation_ticker="CORP",
        )

        AuthUtils.disconnect_signals()
        CharacterOwnership.objects.create(
            user=self.applicant,
            character=eve_char,
            owner_hash="3",
        )
        AuthUtils.connect_signals()

        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_NEW,
            decision=Application.DECISION_PENDING,
        )

        self.assertCountEqual(app.characters, [self.applicant_eve_char, eve_char])

    def test_characters_with_no_char_ownership(self):
        eve_char = EveCharacter.objects.create(
            character_id=3,
            character_name="Applicant 3",
            corporation_id=1,
            corporation_name="Corp",
            corporation_ticker="CORP",
        )

        char = Character.objects.create(
            eve_character=eve_char,
            member=None,
        )

        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=eve_char,
            status=Application.STATUS_NEW,
            decision=Application.DECISION_PENDING,
        )

        self.assertEqual(app.characters, [eve_char])

    def test_reviewer_str(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_REVIEW,
            decision=Application.DECISION_PENDING,
            reviewer=self.officer_eve_char,
        )

        self.assertEqual(app.reviewer_str, self.officer_eve_char.character_name)

    def test_get_status_message(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_NEW,
            decision=Application.DECISION_PENDING,
        )

        self.assertEqual(
            app.get_status_message(), Application.STATUS_MESSAGE[Application.STATUS_NEW]
        )

    def test_get_decision_message(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        app = Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_NEW,
            decision=Application.DECISION_PENDING,
        )

        self.assertEqual(
            app.get_decision_message(),
            Application.DECISION_MESSAGE[Application.DECISION_PENDING],
        )
