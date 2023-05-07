# Django
from django.test import TestCase
from django.utils.dateparse import parse_datetime

# Alliance Auth
from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
from allianceauth.tests.auth_utils import AuthUtils

from ..models import Character, CharacterUpdateStatus


class TestModelCharacterUpdateStatus(TestCase):
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

    def test_str(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        status = CharacterUpdateStatus.objects.create(
            character=char,
            status=CharacterUpdateStatus.STATUS_OKAY,
            updated_on=parse_datetime("2020-01-01 00:00Z"),
        )

        self.assertEqual(str(status), "Applicant 1 [2020-01-01 00:00:00+00:00]: Okay")
