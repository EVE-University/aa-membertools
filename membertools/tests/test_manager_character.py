# Standard Library
from datetime import datetime
from unittest import skip
from unittest.mock import patch

# Django
from django.test import TestCase

# Alliance Auth
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
from allianceauth.eveonline.providers import Corporation, ObjectNotFound

from ..models import Character


@skip("Retiring custom CharacterManager")
class TestManagerCharacter(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.corp = EveCorporationInfo.objects.create(
            corporation_id=10,
            corporation_name="Join Me",
            corporation_ticker="JOIN",
            member_count=20,
        )

        cls.eve_char = EveCharacter.objects.create(
            character_id=10,
            character_name="Some Member",
            corporation_id=cls.corp.corporation_id,
            corporation_name=cls.corp.corporation_name,
            corporation_ticker=cls.corp.corporation_ticker,
        )

        cls.char = Character.objects.create(
            eve_character=cls.eve_char,
            member=None,
        )

        cls.esi_details = {
            "birthday": "2023-01-01T12:00:00Z",
            "bloodline_id": 1,
            "corporation_id": 10,
            "description": "Some Description",
            "gender": "male",
            "name": "Some Member",
            "race_id": 1,
            "security_status": 1.23456,
        }

        cls.corp_provider = Corporation(
            id=10,
            name="Join Me",
            ticker="JOIN",
            members=20,
        )
        return super().setUpTestData()

    def test_update_for_char(self):
        Character.objects.update_for_char(self.char, self.esi_details)
        self.char.refresh_from_db()

        self.assertEqual(self.char.eve_character, self.eve_char)
        self.assertEqual(
            self.char.birthday,
            datetime.fromisoformat(self.esi_details["birthday"].replace("Z", "+00:00")),
        )
        self.assertEqual(self.char.corporation, self.corp)
        self.assertEqual(self.char.alliance, None)
        self.assertEqual(self.char.faction, None)
        self.assertEqual(self.char.description, self.esi_details["description"])
        self.assertAlmostEqual(
            self.char.security_status, self.esi_details["security_status"]
        )

    def test_update_for_char_ubug(self):
        description_result = "A \u3112\u4e47\u4e02\u3112"  # "A ㄒ乇丂ㄒ"
        temp_details = {
            **self.esi_details,
            **{"description": "u'A \\u3112\\u4e47\\u4e02\\u3112'"},
        }
        Character.objects.update_for_char(self.char, temp_details)
        self.char.refresh_from_db()
        self.assertEqual(self.char.eve_character, self.eve_char)
        self.assertEqual(
            self.char.birthday,
            datetime.fromisoformat(self.esi_details["birthday"].replace("Z", "+00:00")),
        )
        self.assertEqual(self.char.corporation, self.corp)
        self.assertEqual(self.char.alliance, None)
        self.assertEqual(self.char.faction, None)
        self.assertEqual(self.char.description, description_result)
        self.assertAlmostEqual(
            self.char.security_status, self.esi_details["security_status"]
        )

    def test_update_for_char_ubug_invalid(self):
        temp_details = {
            **self.esi_details,
            **{"description": "u'A \\u3112\\u4e47\\u4exz\\u3112'"},
        }

        Character.objects.update_for_char(self.char, temp_details)
        self.char.refresh_from_db()

        self.assertEqual(self.char.description, "")

    @patch(
        "allianceauth.eveonline.models.EveCorporationInfo.objects.provider.get_corporation"
    )
    def test_update_for_char_non_existant_corp(self, mock_corp_provider):
        mock_corp_provider.side_effect = ObjectNotFound(10, "corporation")
        self.corp.delete()

        with self.assertRaises(ObjectNotFound):
            Character.objects.update_for_char(self.char, self.esi_details)
