# Standard Library
import datetime

# Django
from django.test import TestCase

# Alliance Auth
from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
from allianceauth.tests.auth_utils import AuthUtils

from ..models import (
    Application,
    ApplicationAction,
    ApplicationForm,
    ApplicationQuestion,
    Character,
)


class TestManagerAppAction(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.corp = EveCorporationInfo.objects.create(
            corporation_id=10,
            corporation_name="Join Me",
            corporation_ticker="JOIN",
            member_count=20,
        )
        cls.app_form_question = ApplicationQuestion.objects.create(
            title="Text Question",
            help_text="A text question",
        )
        cls.corp_app_form = ApplicationForm.objects.create(corp=cls.corp)
        cls.corp_app_form.questions.add(cls.app_form_question)

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

        AuthUtils.connect_signals()

        return super().setUpTestData()

    def test_create_action(self):
        # TODO: Update ApplicationAction model and manager to use EveCharacter instead of User.
        self.skipTest("Needs model and manager update")

        action_on = datetime.datetime(2000, 1, 1, 20, 0, 0, 0, datetime.timezone.utc)

        char = Character.objects.create(
            eve_character=self.applicant_1_eve_char,
            member=None,
        )

        app = Application.objects.create(
            form=self.corp_app_form,
            eve_character=self.applicant_eve_char,
            character=char,
            status=Application.STATUS_NEW,
        )

        ApplicationAction.objects.create_action(
            application=app,
            action=ApplicationAction.ACCEPT,
            action_by=self.officer_eve_char,
            action_on=action_on,
            override_by=None,
        )
