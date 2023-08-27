# Standard Library
# from datetime import datetime
# Standard Library
from unittest.mock import Mock, patch

# Third Party
from app_utils.testing import NoSocketsTestCase

# Django
from django.utils.dateparse import parse_datetime

# Alliance Auth
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo

from ..models import Character, CharacterCorpHistory

# from allianceauth.eveonline.providers import Corporation, ObjectNotFound


class TestManagerCharacterCorpHistory(NoSocketsTestCase):
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

        cls.esi_one_corp = [
            {
                "corporation_id": 10,
                "record_id": 1,
                "start_date": parse_datetime("2020-01-01 00:01Z"),
                "is_deleted": False,
            }
        ]

        cls.esi_three_corp = [
            {
                "corporation_id": 10,
                "record_id": 3,
                "start_date": parse_datetime("2023-01-01 00:01Z"),
                "is_deleted": False,
            },
            {
                "corporation_id": 10,
                "record_id": 2,
                "start_date": parse_datetime("2022-01-01 00:01Z"),
                "is_deleted": False,
            },
            {
                "corporation_id": 10,
                "record_id": 1,
                "start_date": parse_datetime("2021-01-01 00:01Z"),
                "is_deleted": False,
            },
        ]

        return super().setUpTestData()

    def test_update_char_no_corp_history(self):
        self.assertFalse(self.char.corporation_history.exists())
        CharacterCorpHistory.objects.update_char(self.char, [])
        self.assertFalse(self.char.corporation_history.exists())

    @patch(
        "allianceauth.eveonline.models.EveCorporationInfo.objects.update_corporation"
    )
    def test_update_char_one_corp_history(self, updatecorp_mock: Mock):
        updatecorp_mock.return_value = self.corp
        self.assertFalse(self.char.corporation_history.exists())
        CharacterCorpHistory.objects.update_char(self.char, self.esi_one_corp)
        updatecorp_mock.assert_called()
        self.assertTrue(self.char.corporation_history.exists())
        history_row = self.char.corporation_history.all()[0]
        esi_row = self.esi_one_corp[0]
        self.assertEqual(
            history_row.corporation.corporation_id, esi_row["corporation_id"]
        )
        self.assertEqual(history_row.record_id, esi_row["record_id"])
        self.assertEqual(history_row.start_date, esi_row["start_date"])
        self.assertEqual(history_row.is_deleted, esi_row["is_deleted"])
        self.assertTrue(history_row.is_last)

    @patch(
        "allianceauth.eveonline.models.EveCorporationInfo.objects.create_corporation"
    )
    @patch(
        "allianceauth.eveonline.models.EveCorporationInfo.objects.update_corporation"
    )
    def test_update_char_one_corp_history_unknown_corp(
        self, updatecorp_mock: Mock, createcorp_mock: Mock
    ):
        updatecorp_mock.side_effect = EveCorporationInfo.DoesNotExist
        createcorp_mock.return_value = self.corp
        self.assertFalse(self.char.corporation_history.exists())
        CharacterCorpHistory.objects.update_char(self.char, self.esi_one_corp)
        updatecorp_mock.assert_called()
        createcorp_mock.assert_called()
        self.assertTrue(self.char.corporation_history.exists())
        history_row = self.char.corporation_history.all()[0]
        esi_row = self.esi_one_corp[0]
        self.assertEqual(
            history_row.corporation.corporation_id, esi_row["corporation_id"]
        )
        self.assertEqual(history_row.record_id, esi_row["record_id"])
        self.assertEqual(history_row.start_date, esi_row["start_date"])
        self.assertEqual(history_row.is_deleted, esi_row["is_deleted"])
        self.assertTrue(history_row.is_last)

    @patch(
        "allianceauth.eveonline.models.EveCorporationInfo.objects.update_corporation"
    )
    def test_update_char_three_corp_history(self, updatecorp_mock: Mock):
        updatecorp_mock.return_value = self.corp
        self.assertFalse(self.char.corporation_history.exists())
        CharacterCorpHistory.objects.update_char(self.char, self.esi_three_corp)
        self.assertEqual(updatecorp_mock.call_count, 3)
        self.assertEqual(self.char.corporation_history.count(), 3)

        history = self.char.corporation_history.all()
        for i in range(3):
            history_row = history[i]
            esi_row = self.esi_three_corp[i]
            self.assertEqual(
                history_row.corporation.corporation_id, esi_row["corporation_id"]
            )
            self.assertEqual(history_row.record_id, esi_row["record_id"])
            self.assertEqual(history_row.start_date, esi_row["start_date"])
            self.assertEqual(history_row.is_deleted, esi_row["is_deleted"])
            self.assertEqual(history_row.is_last, (i == 2))
