# Standard Library
import datetime

# Django
from django.db import IntegrityError
from django.test import TestCase

# Alliance Auth
from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
from allianceauth.tests.auth_utils import AuthUtils

from ..models import (
    Application,
    ApplicationForm,
    ApplicationQuestion,
    ApplicationResponse,
    Character,
)


class TestModelAppResponse(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.corp = EveCorporationInfo.objects.create(
            corporation_id=10,
            corporation_name="Join Me",
            corporation_ticker="JOIN",
            member_count=20,
        )
        cls.corp_app_form = ApplicationForm.objects.create(corp=cls.corp)
        cls.corp_app_form_question = ApplicationQuestion.objects.create(
            title="Text Question",
            help_text="A text question",
        )
        cls.corp_app_form.questions.add(cls.corp_app_form_question)

        cls.applicant = AuthUtils.create_user("Applicant_1")

        cls.applicant_eve_char = EveCharacter.objects.create(
            character_id=1,
            character_name="Applicant 1",
            corporation_id=1,
            corporation_name="Corp",
            corporation_ticker="CORP",
        )

        cls.applicant_char = Character.objects.create(
            eve_character=cls.applicant_eve_char,
            member=None,
        )

        cls.applicant.profile.main_character = cls.applicant_eve_char
        cls.applicant.profile.save()

        CharacterOwnership.objects.create(
            user=cls.applicant,
            character=cls.applicant_eve_char,
            owner_hash="1",
        )

        return super().setUpTestData()

    def test_str(self):
        test_datetime = datetime.datetime(2020, 1, 1, 1, 0, 0, 0, datetime.timezone.utc)
        app = Application.objects.create(
            form=self.corp_app_form,
            character=self.applicant_char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_NEW,
            decision=Application.DECISION_PENDING,
            submitted_on=test_datetime,
        )

        response = ApplicationResponse.objects.create(
            question=self.corp_app_form_question,
            application=app,
            answer="Test",
        )

        self.assertEqual(
            str(response), "Join Me (01/01/2020) Answer To Question: Text Question"
        )

    def test_unique_together_question_answer(self):
        app = Application.objects.create(
            form=self.corp_app_form,
            character=self.applicant_char,
            eve_character=self.applicant_eve_char,
            status=Application.STATUS_NEW,
            decision=Application.DECISION_PENDING,
        )

        ApplicationResponse.objects.create(
            question=self.corp_app_form_question,
            application=app,
            answer="Test",
        )

        with self.assertRaises(IntegrityError):
            ApplicationResponse.objects.create(
                question=self.corp_app_form_question,
                application=app,
                answer="Test2",
            )
