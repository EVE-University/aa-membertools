# Django
from django.db import IntegrityError
from django.test import TestCase
from django.utils.dateparse import parse_datetime

# Alliance Auth
from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
from allianceauth.tests.auth_utils import AuthUtils

from ..models import Character, CharacterCorpHistory


class TestModelCharacterCorpHistory(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.corp = EveCorporationInfo.objects.create(
            corporation_id=10,
            corporation_name="Join Me",
            corporation_ticker="JOIN",
            member_count=20,
        )

        # Make some users/mains
        AuthUtils.disconnect_signals()

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

    def test_unique_character_record_id(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        CharacterCorpHistory.objects.create(
            character=char,
            corporation=self.corp,
            record_id=1,
            start_date=parse_datetime("2020-01-01 00:00Z"),
        )

        with self.assertRaises(IntegrityError):
            CharacterCorpHistory.objects.create(
                character=char,
                corporation=self.corp,
                record_id=1,
                start_date=parse_datetime("2020-01-01 00:00Z"),
            )

    def test_str(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        history = CharacterCorpHistory.objects.create(
            character=char,
            corporation=self.corp,
            record_id=1,
            start_date=parse_datetime("2020-01-01 00:00Z"),
        )

        self.assertEqual(str(history), "Applicant 1-1")
