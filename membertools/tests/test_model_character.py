# Standard Library
from unittest.mock import Mock, patch

# Django
from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from django.utils.dateparse import parse_datetime

# Alliance Auth
from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import (
    EveAllianceInfo,
    EveCharacter,
    EveCorporationInfo,
    EveFactionInfo,
)
from allianceauth.eveonline.providers import Entity, ObjectNotFound
from allianceauth.tests.auth_utils import AuthUtils

from ..models import (  # Member,
    ApplicationForm,
    ApplicationQuestion,
    ApplicationTitle,
    Character,
)


class TestModelCharacter(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.orig_get_model = apps.get_model
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

        cls.esi_details = {
            "birthday": parse_datetime("2023-01-01T12:00:00"),
            "bloodline_id": 1,
            "corporation_id": 10,
            "description": "Some Description",
            "gender": "male",
            "name": "Member 1",
            "race_id": 1,
            "security_status": 1.23456,
            "title": "Vanity Title",
        }

        return super().setUpTestData()

    def test_character_name(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertEqual(char.character_name, self.applicant_eve_char.character_name)

    def test_character_ownership_owned_char(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertNotEqual(char.character_ownership, None)
        self.assertEqual(
            char.character_ownership, self.applicant_eve_char.character_ownership
        )

    def test_character_ownership_unowned_char(self):
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

        self.assertEqual(char.character_ownership, None)

    def test_user_owned_char(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertNotEqual(char.user, None)
        self.assertEqual(char.user, self.applicant)

    def test_user_unowned_char(self):
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

        self.assertEqual(char.user, None)

    def test_main_character_owned_char(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertNotEqual(char.main_character, None)
        self.assertEqual(char.main_character, self.applicant_eve_char)

    def test_main_character_unowned_char(self):
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

        self.assertEqual(char.main_character, None)

    def test_description_text_only_whitespace(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
            description="       ",
        )

        self.assertEqual(char.description_text, None)

    def test_description_text_strip_tags(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
            description='<script>alert("alert");</script>',
        )

        self.assertEqual(char.description_text, 'alert("alert");')

    def test_description_text_strip_confusable_tags(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
            description='\ufe64script\ufe65alert("alert");\ufe64/script\ufe65',
        )

        self.assertEqual(char.description_text, 'alert("alert");')

    @patch("django.apps.apps.get_model")
    def test__get_ma_character_model_lookup_error(self, model_mock):
        # Make sure we only patch the get_model() return for the appropriate model
        def _side_effect(*args, **kwargs):
            if args[0] == "memberaudit" and args[1] == "Character":
                raise LookupError()
            return TestModelCharacter.orig_get_model(*args, **kwargs)

        model_mock.side_effect = _side_effect

        # pylint: disable=protected-access
        ret = Character._get_ma_character(self.applicant_eve_char)

        model_mock.assert_called_with("memberaudit", "Character")
        self.assertEqual(ret, None)

    @patch("django.apps.apps.get_model")
    def test__get_ma_character_not_exists(self, model_mock):
        ma_char_mock = Mock()
        ma_char_mock.objects.get.side_effect = ObjectDoesNotExist

        # Make sure we only patch the get_model() return for the appropriate model
        def _side_effect(*args, **kwargs):
            if args[0] == "memberaudit" and args[1] == "Character":
                return ma_char_mock
            return TestModelCharacter.orig_get_model(*args, **kwargs)

        model_mock.side_effect = _side_effect

        # pylint: disable=protected-access
        ret = Character._get_ma_character(self.applicant_eve_char)

        ma_char_mock.objects.get.assert_called_with(
            eve_character=self.applicant_eve_char
        )
        self.assertEqual(ret, None)

    # Would this be excessive testing or confirmation testing? :P
    @patch("membertools.models.Character._get_ma_character")
    def test_memberaudit_character_exists(self, ma_char_mock):
        ma_char_mock.return_value = Mock()

        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertEqual(char.memberaudit_character, ma_char_mock.return_value)

    @patch("membertools.models.Character._get_ma_character")
    def test_memberaudit_character_not_exists(self, ma_char_mock):
        ma_char_mock.return_value = None

        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertEqual(char.memberaudit_character, None)

    @patch("membertools.models.Character._get_ma_character")
    def test_memberaudit_update_status_not_exists(self, ma_char_mock):
        ma_char_mock.return_value = None

        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertEqual(char.memberaudit_update_status, "Not Registered")

    @patch("membertools.models.Character._get_ma_character")
    def test_memberaudit_update_status_okay(self, ma_char_mock):
        ma_char_mock.return_value.is_update_status_ok.return_value = True

        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertEqual(char.memberaudit_update_status, "Okay")

    @patch("membertools.models.Character._get_ma_character")
    def test_memberaudit_update_status_updating(self, ma_char_mock):
        ma_char_mock.return_value.is_update_status_ok.return_value = None

        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertEqual(char.memberaudit_update_status, "Updating")

    @patch("membertools.models.Character._get_ma_character")
    def test_memberaudit_update_status_error(self, ma_char_mock):
        ma_char_mock.return_value.is_update_status_ok.return_value = False

        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertEqual(char.memberaudit_update_status, "Error")

    @patch("membertools.models.Character._get_ma_character")
    def test_memberaudit_last_updated_char_not_exists(self, ma_char_mock):
        ma_char_mock.return_value = None

        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertEqual(char.memberaudit_last_updated, None)

    @patch("membertools.models.Character._get_ma_character")
    def test_memberaudit_last_updated_no_char_update_exists(self, ma_char_mock):
        ma_char_mock.return_value.update_status_set = Mock(spec=[])

        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertEqual(char.memberaudit_last_updated, None)

    @patch("membertools.models.Character._get_ma_character")
    def test_memberaudit_last_updated_no_char_update_success_exists(self, ma_char_mock):
        ma_char_mock.return_value.update_status_set.filter.side_effect = (
            ObjectDoesNotExist
        )

        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertEqual(char.memberaudit_last_updated, None)

    @patch("membertools.models.Character._get_ma_character")
    def test_memberaudit_last_updated_success(self, ma_char_mock):
        test_datetime = parse_datetime("2020-01-01 00:00Z")
        ma_char_mock.return_value.update_status_set.filter.return_value.latest.return_value.run_finished_at = (
            test_datetime
        )

        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertEqual(char.memberaudit_last_updated, test_datetime)

    @patch("membertools.models.Character._get_ma_character")
    def test_location_char_exists(self, ma_char_mock):
        # This property actually returns memberaudit.models.general.Location, but we don't have to
        # mock or use that type here for the test to effectively be valid.
        ma_char_mock.return_value.location.location = "Location"

        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertEqual(char.location, "Location")

    @patch("membertools.models.Character._get_ma_character")
    def test_location_char_not_exists(self, ma_char_mock):
        ma_char_mock.return_value.location.location = None

        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertEqual(char.location, None)

    @patch("membertools.models.Character._get_ma_character")
    def test_skillpoints_total_char_exists(self, ma_char_mock):
        ma_char_mock.return_value.skillpoints.total = 12_345_678

        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertEqual(char.skillpoints_total, 12_345_678)

    @patch("membertools.models.Character._get_ma_character")
    def test_skillpoints_total_char_not_exists(self, ma_char_mock):
        ma_char_mock.return_value.skillpoints.total = None

        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertEqual(char.skillpoints_total, None)

    @patch("membertools.models.Character._get_ma_character")
    def test_skillpoints_unalloc_char_exists(self, ma_char_mock):
        ma_char_mock.return_value.skillpoints.unallocated = 1_234_567

        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertEqual(char.skillpoints_unallocated, 1_234_567)

    @patch("membertools.models.Character._get_ma_character")
    def test_skillpoints_unalloc_char_not_exists(self, ma_char_mock):
        ma_char_mock.return_value.skillpoints.unallocated = None

        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertEqual(char.skillpoints_unallocated, None)

    @patch("membertools.models.Character._get_ma_character")
    def test_wallet_balance_char_exists(self, ma_char_mock):
        ma_char_mock.return_value.wallet_balance.total = 1_234_567

        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertEqual(char.wallet_balance, 1_234_567)

    @patch("membertools.models.Character._get_ma_character")
    def test_wallet_balance_char_not_exists(self, ma_char_mock):
        ma_char_mock.return_value.wallet_balance.total = None

        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertEqual(char.wallet_balance, None)

    @patch("membertools.models.Character._get_ma_character")
    def test_online_last_login_char_exists(self, ma_char_mock):
        ma_char_mock.return_value.online_status.last_login = "01/01/2020"

        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertEqual(char.online_last_login, "01/01/2020")

    @patch("membertools.models.Character._get_ma_character")
    def test_online_last_login_char_not_exists(self, ma_char_mock):
        ma_char_mock.return_value.online_status.last_login = None

        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertEqual(char.online_last_login, None)

    def test_is_main_exists(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertEqual(char.is_main(), True)

    def test_is_main_not_exists(self):
        eve_char = EveCharacter.objects.create(
            character_id=3,
            character_name="Applicant 3",
            corporation_id=1,
            corporation_name="Corp",
            corporation_ticker="CORP",
        )

        AuthUtils.disconnect_signals()

        user = AuthUtils.create_user("Applicant_3")

        CharacterOwnership.objects.create(
            user=user,
            character=eve_char,
            owner_hash="3",
        )

        AuthUtils.connect_signals()

        char = Character.objects.create(
            eve_character=eve_char,
            member=None,
        )

        self.assertEqual(char.is_main(), False)

    def test_str(self):
        char = Character.objects.create(
            eve_character=self.applicant_eve_char,
            member=None,
        )

        self.assertEqual(str(char), "Applicant 1")

    def test_update_char_details_description_ubug(self):
        description_result = "A \u3112\u4e47\u4e02\u3112"  # "A ㄒ乇丂ㄒ"
        temp_details = {
            **self.esi_details,
            **{"description": "u'A \\u3112\\u4e47\\u4e02\\u3112'"},
        }

        char = Character.objects.create(
            eve_character=self.member_eve_char,
            member=None,
        )

        char.update_character_details(temp_details)

        self.assertEqual(char.eve_character, self.member_eve_char)
        self.assertEqual(
            char.birthday,
            temp_details["birthday"],
        )
        self.assertEqual(char.corporation, self.corp)
        self.assertEqual(char.alliance, None)
        self.assertEqual(char.faction, None)
        self.assertAlmostEqual(char.security_status, temp_details["security_status"])
        self.assertEqual(char.description, description_result)

    def test_update_char_details_description_ubug_invalid(self):
        temp_details = {
            **self.esi_details,
            **{"description": "u'A \\u3112\\u4e47\\u4exz\\u3112'"},
        }

        char = Character.objects.create(
            eve_character=self.member_eve_char,
            member=None,
        )

        char.update_character_details(temp_details)

        self.assertEqual(char.description, "")

    @patch(
        "allianceauth.eveonline.models.EveCorporationInfo.objects.provider.get_corporation"
    )
    def test_update_char_details_corp(self, mock_corp_provider):
        mock_corp_provider.side_effect = ObjectNotFound(10, "corporation")

        char = Character.objects.create(
            eve_character=self.member_eve_char,
            member=None,
        )

        char.update_character_details(self.esi_details)
        self.assertEqual(char.corporation, self.corp)
        self.assertEqual(char.alliance, None)
        mock_corp_provider.assert_not_called()

    @patch(
        "allianceauth.eveonline.models.EveCorporationInfo.objects.provider.get_corporation"
    )
    def test_update_char_details_non_existent_corp(self, mock_corp_provider):
        mock_corp_provider.side_effect = ObjectNotFound(10, "corporation")
        self.corp.delete()

        char = Character.objects.create(
            eve_character=self.member_eve_char,
            member=None,
        )

        with self.assertRaises(ObjectNotFound):
            char.update_character_details(self.esi_details)

    @patch(
        "allianceauth.eveonline.models.EveAllianceInfo.objects.provider.get_alliance"
    )
    def test_update_char_details_alliance(self, mock_alliance_provider):
        temp_details = {
            **self.esi_details,
            **{"alliance_id": 1},
        }

        alliance = EveAllianceInfo.objects.create(
            alliance_id=1,
            alliance_name="The Join Us Alliance",
            alliance_ticker="JOINUS",
            executor_corp_id=10,
        )

        self.corp.alliance = alliance
        self.corp.save()

        char = Character.objects.create(
            eve_character=self.member_eve_char,
            member=None,
        )

        char.update_character_details(temp_details)

        self.assertEqual(char.alliance, alliance)
        mock_alliance_provider.assert_not_called()

    @patch(
        "allianceauth.eveonline.models.EveAllianceInfo.objects.provider.get_alliance"
    )
    def test_update_char_details_non_existent_alliance(self, mock_alliance_provider):
        temp_details = {
            **self.esi_details,
            **{"alliance_id": 1},
        }

        mock_alliance_provider.side_effect = ObjectNotFound(1, "alliance")

        char = Character.objects.create(
            eve_character=self.member_eve_char,
            member=None,
        )

        with self.assertRaises(ObjectNotFound):
            char.update_character_details(temp_details)

        self.assertEqual(char.alliance, None)
        mock_alliance_provider.assert_called()

    @patch("allianceauth.eveonline.models.EveFactionInfo.provider.get_faction")
    def test_update_char_details_faction(self, mock_faction_provider):
        temp_details = {
            **self.esi_details,
            **{"faction_id": 1},
        }

        faction = EveFactionInfo.objects.create(
            faction_id=1,
            faction_name="The Faction",
        )

        char = Character.objects.create(
            eve_character=self.member_eve_char,
            member=None,
        )

        char.update_character_details(temp_details)

        self.assertEqual(char.faction, faction)
        mock_faction_provider.assert_not_called()

    @patch("allianceauth.eveonline.providers.EveSwaggerProvider.get_faction")
    def test_update_char_details_non_existent_faction(self, mock_faction_provider):
        mock_faction_provider.side_effect = ObjectNotFound(1, "faction")
        faction = Entity(id=1, name="The Faction")

        temp_details = {
            **self.esi_details,
            **{
                "faction_id": 1,
                "faction": faction,
            },
        }

        char = Character.objects.create(
            eve_character=self.member_eve_char,
            member=None,
        )

        self.assertEqual(char.faction, None)

        with self.assertRaises(ObjectNotFound):
            char.update_character_details(temp_details)
            self.assertEqual(char.faction, None)
            mock_faction_provider.assert_called()

    def test_update_char_details_new_corp(self):
        corp = EveCorporationInfo.objects.create(
            corporation_id=50,
            corporation_name="Leave Me",
            corporation_ticker="LEAVE",
            member_count=2,
        )

        char = Character.objects.create(
            eve_character=self.member_eve_char,
            member=None,
            corporation=corp,
        )

        self.assertEqual(char.corporation, corp)

        char.update_character_details(self.esi_details)

        self.assertEqual(char.corporation, self.corp)

    def test_update_char_details_birthday(self):
        char = Character.objects.create(
            eve_character=self.member_eve_char,
            member=None,
            corporation=self.corp,
        )

        char.update_character_details(self.esi_details)
        self.assertEqual(char.birthday, self.esi_details["birthday"])

    def test_update_char_details_security_status(self):
        char = Character.objects.create(
            eve_character=self.member_eve_char,
            member=None,
            corporation=self.corp,
        )

        char.update_character_details(self.esi_details)
        self.assertAlmostEqual(
            char.security_status, self.esi_details["security_status"]
        )

    def test_update_char_details_title(self):
        char = Character.objects.create(
            eve_character=self.member_eve_char,
            member=None,
            corporation=self.corp,
        )

        char.update_character_details(self.esi_details)
        self.assertEqual(char.title, self.esi_details["title"])

    def test_update_corp_history(self):
        self.skipTest("Corp history is disabled by CCP")
