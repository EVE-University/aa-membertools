# Standard Library
# import datetime
# from unittest.mock import patch

# Django
# from django.core.exceptions import ValidationError
from django.test import TestCase

# Alliance Auth
from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
from allianceauth.tests.auth_utils import AuthUtils

from ..models import (  # Application,; ApplicationAction,; Member,
    ApplicationForm,
    ApplicationQuestion,
    ApplicationTitle,
    Character,
    Comment,
)

# from django.utils import timezone


class TestComment(TestCase):
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

        return super().setUpTestData()

    def test_str(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )
        comment = Comment.objects.create(
            character=char, poster=self.officer_eve_char, text="Test"
        )

        self.assertEqual(str(comment), "Recruitment Officer comment on None")
