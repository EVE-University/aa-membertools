# Standard Library
import datetime
from unittest.mock import patch

# Third Party
from app_utils.testing import NoSocketsTestCase

# Django
from django.utils.dateparse import parse_datetime

# Alliance Auth
from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
from allianceauth.tests.auth_utils import AuthUtils

from ..models import ApplicationForm, ApplicationQuestion, ApplicationTitle, Member


class TestModelMember(NoSocketsTestCase):
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

    def test_character_ownership_owned(self):
        member = Member.objects.create(
            main_character=self.applicant_eve_char,
            first_main_character=self.applicant_eve_char,
        )

        self.assertNotEqual(member.character_ownership, None)
        self.assertEqual(
            member.character_ownership, self.applicant_eve_char.character_ownership
        )

    def test_character_ownership_unowned(self):
        eve_char = EveCharacter.objects.create(
            character_id=3,
            character_name="Applicant 3",
            corporation_id=1,
            corporation_name="Corp",
            corporation_ticker="CORP",
        )

        member = Member.objects.create(
            main_character=eve_char,
            first_main_character=eve_char,
        )

        self.assertEqual(member.character_ownership, None)

    def test_user_owned(self):
        member = Member.objects.create(
            main_character=self.applicant_eve_char,
            first_main_character=self.applicant_eve_char,
        )

        self.assertNotEqual(member.user, None)
        self.assertEqual(
            member.user,
            self.applicant_eve_char.character_ownership.user,
        )

    def test_user_unowned(self):
        eve_char = EveCharacter.objects.create(
            character_id=3,
            character_name="Applicant 3",
            corporation_id=1,
            corporation_name="Corp",
            corporation_ticker="CORP",
        )

        member = Member.objects.create(
            main_character=eve_char,
            first_main_character=eve_char,
        )

        self.assertEqual(member.user, None)

    def test_characters_single_owned(self):
        member = Member.objects.create(
            main_character=self.applicant_eve_char,
            first_main_character=self.applicant_eve_char,
        )

        self.assertEqual(member.characters, [self.applicant_eve_char])

    def test_characters_multi_owned(self):
        member = Member.objects.create(
            main_character=self.applicant_eve_char,
            first_main_character=self.applicant_eve_char,
        )

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

        self.assertCountEqual(member.characters, [self.applicant_eve_char, eve_char])

    def test_characters_none_owned(self):
        eve_char = EveCharacter.objects.create(
            character_id=3,
            character_name="Applicant 3",
            corporation_id=1,
            corporation_name="Corp",
            corporation_ticker="CORP",
        )

        member = Member.objects.create(
            main_character=eve_char,
            first_main_character=eve_char,
        )

        self.assertEqual(member.characters, [eve_char])

    # Patching the SwaggerClient results in the same mocked client being reused in
    # other tests that use the client. So, we can only accurately run this test once.
    @patch("esi.clients.SwaggerClient")
    @patch("membertools.models.MEMBERTOOLS_MAIN_CORP_ID", 10)
    def test_update_joined_dates_once(self, client_mock):
        self.skipTest("Need to update joined date tests to use swagger stub client")
        test_datetime = datetime.datetime(2020, 1, 2, 1, 0, 0, 0, datetime.timezone.utc)
        history_data = [
            {
                "corporation_id": self.corp.corporation_id,
                "is_deleted": False,
                "record_id": 2,
                "start_date": parse_datetime("2020-01-02T01:00:00Z"),
            },
            {
                "corporation_id": 1,
                "is_deleted": False,
                "record_id": 1,
                "start_date": parse_datetime("2020-01-01T01:00:00Z"),
            },
        ]
        client_mock.from_spec.return_value.Character.get_characters_character_id_corporationhistory.return_value.results.return_value = (
            history_data
        )

        member = Member.objects.create(
            main_character=self.member_eve_char,
            first_main_character=self.member_eve_char,
        )

        member.update_joined_dates()

        client_mock.from_spec.return_value.Character.get_characters_character_id_corporationhistory.assert_called()
        client_mock.from_spec.return_value.Character.get_characters_character_id_corporationhistory.return_value.results.assert_called()

        self.assertEqual(member.first_joined, test_datetime)
        self.assertEqual(member.last_joined, test_datetime)

    @patch("esi.clients.SwaggerClient")
    @patch("membertools.models.MEMBERTOOLS_MAIN_CORP_ID", 10)
    def test_update_joined_dates_twice(self, client_mock):
        test_datetime = datetime.datetime(2020, 1, 2, 1, 0, 0, 0, datetime.timezone.utc)
        test_datetime_2 = datetime.datetime(
            2020, 1, 4, 1, 0, 0, 0, datetime.timezone.utc
        )
        history_data = [
            {
                "corporation_id": self.corp.corporation_id,
                "is_deleted": False,
                "record_id": 4,
                "start_date": parse_datetime("2020-01-04T01:00:00Z"),
            },
            {
                "corporation_id": 1,
                "is_deleted": False,
                "record_id": 3,
                "start_date": parse_datetime("2020-01-03T01:00:00Z"),
            },
            {
                "corporation_id": self.corp.corporation_id,
                "is_deleted": False,
                "record_id": 2,
                "start_date": parse_datetime("2020-01-02T01:00:00Z"),
            },
            {
                "corporation_id": 1,
                "is_deleted": False,
                "record_id": 1,
                "start_date": parse_datetime("2020-01-01T01:00:00Z"),
            },
        ]

        client_mock.from_spec.return_value.Character.get_characters_character_id_corporationhistory.return_value.results.return_value = (
            history_data
        )

        member = Member.objects.create(
            main_character=self.member_eve_char,
            first_main_character=self.member_eve_char,
        )

        self.assertTrue(member.update_joined_dates())

        client_mock.from_spec.return_value.Character.get_characters_character_id_corporationhistory.assert_called()
        client_mock.from_spec.return_value.Character.get_characters_character_id_corporationhistory.return_value.results.assert_called()

        self.assertEqual(member.first_joined, test_datetime)
        self.assertEqual(member.last_joined, test_datetime_2)

    def test_str_with_main(self):
        member = Member.objects.create(
            main_character=self.applicant_eve_char,
            first_main_character=self.applicant_eve_char,
        )

        self.assertEqual(str(member), "Applicant 1")
