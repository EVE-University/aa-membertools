# Django
from django.test import TestCase

# Alliance Auth
from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
from allianceauth.tests.auth_utils import AuthUtils

from ..models import (
    ApplicationForm,
    ApplicationQuestion,
    ApplicationTitle,
    Character,
    Member,
    TitleFilter,
)


class TestModelTitleFilter(TestCase):
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
        cls.other_title = ApplicationTitle.objects.create(
            name="Other Title", priority=2
        )

        # Make some users/mains
        AuthUtils.disconnect_signals()

        cls.user = AuthUtils.create_user("Character_1")

        cls.eve_char = EveCharacter.objects.create(
            character_id=1,
            character_name="Character 1",
            corporation_id=1,
            corporation_name="Corp",
            corporation_ticker="CORP",
        )

        cls.user.profile.main_character = cls.eve_char
        cls.user.profile.save()

        CharacterOwnership.objects.create(
            user=cls.user,
            character=cls.eve_char,
            owner_hash="1",
        )

        AuthUtils.connect_signals()

        return super().setUpTestData()

    def test_str(self):
        test_filter = TitleFilter(
            description="Test Filter",
        )

        self.assertEqual(str(test_filter), "Titles Filter: Test Filter")

    def test_name(self):
        test_filter = TitleFilter(
            description="Test Filter",
        )

        self.assertEqual(test_filter.name, "Titles Filter")

    def test_process_filter_has_awarded(self):
        member = Member.objects.create(
            main_character=self.eve_char,
            first_main_character=self.eve_char,
            awarded_title=self.title,
        )
        Character(
            eve_character=self.eve_char,
            member=member,
        )

        test_filter = TitleFilter.objects.create(
            description="Test Filter",
        )
        test_filter.awarded_titles.add(self.title)

        ret = test_filter.process_filter(self.user)

        self.assertEqual(ret, True)

    def test_process_filter_not_awarded(self):
        member = Member.objects.create(
            main_character=self.eve_char,
            first_main_character=self.eve_char,
            awarded_title=self.title,
        )
        Character(
            eve_character=self.eve_char,
            member=member,
        )

        test_filter = TitleFilter.objects.create(
            description="Test Filter",
        )
        test_filter.awarded_titles.add(self.other_title)

        ret = test_filter.process_filter(self.user)

        self.assertEqual(ret, False)

    def test_process_filter_has_applied(self):
        member = Member.objects.create(
            main_character=self.eve_char,
            first_main_character=self.eve_char,
        )
        Character(
            eve_character=self.eve_char,
            member=member,
            applied_title=self.title,
        )

        test_filter = TitleFilter.objects.create(
            description="Test Filter",
        )
        test_filter.applied_titles.add(self.title)

        ret = test_filter.process_filter(self.user)
        self.assertEqual(ret, True)

    def test_process_filter_not_applied(self):
        member = Member.objects.create(
            main_character=self.eve_char,
            first_main_character=self.eve_char,
        )
        Character(
            eve_character=self.eve_char,
            member=member,
            applied_title=self.title,
        )

        test_filter = TitleFilter.objects.create(
            description="Test Filter",
        )
        test_filter.applied_titles.add(self.other_title)

        ret = test_filter.process_filter(self.user)

        self.assertEqual(ret, False)

    def test_process_filter_has_awarded_has_applied(self):
        member = Member.objects.create(
            main_character=self.eve_char,
            first_main_character=self.eve_char,
            awarded_title=self.title,
        )
        Character(
            eve_character=self.eve_char,
            member=member,
            applied_title=self.title,
        )

        test_filter = TitleFilter.objects.create(
            description="Test Filter",
        )
        test_filter.awarded_titles.add(self.title)
        test_filter.applied_titles.add(self.title)

        ret = test_filter.process_filter(self.user)
        self.assertEqual(ret, True)

    def test_process_filter_has_awarded_not_applied(self):
        member = Member.objects.create(
            main_character=self.eve_char,
            first_main_character=self.eve_char,
        )
        Character(
            eve_character=self.eve_char,
            member=member,
            applied_title=self.title,
        )

        test_filter = TitleFilter.objects.create(
            description="Test Filter",
        )
        test_filter.awarded_titles.add(self.title)
        test_filter.applied_titles.add(self.other_title)

        ret = test_filter.process_filter(self.user)

        self.assertFalse(ret)

    def test_audit_filter_awarded_single_member(self):
        member = Member.objects.create(
            main_character=self.eve_char,
            first_main_character=self.eve_char,
            awarded_title=self.title,
        )
        Character.objects.create(
            eve_character=self.eve_char,
            member=member,
        )

        test_filter = TitleFilter.objects.create(
            description="Test Filter",
        )
        test_filter.awarded_titles.add(self.title)

        ret = test_filter.audit_filter([self.user.pk])

        self.assertTrue(ret[self.user.pk]["check"])

    def test_audit_filter_awarded_multi_member(self):
        member = Member.objects.create(
            main_character=self.eve_char,
            first_main_character=self.eve_char,
            awarded_title=self.title,
        )
        Character.objects.create(
            eve_character=self.eve_char,
            member=member,
        )

        AuthUtils.disconnect_signals()

        user_2 = AuthUtils.create_user("Character_2")

        eve_char_2 = EveCharacter.objects.create(
            character_id=2,
            character_name="Character 2",
            corporation_id=1,
            corporation_name="Corp",
            corporation_ticker="CORP",
        )

        user_2.profile.main_character = eve_char_2
        user_2.profile.save()

        CharacterOwnership.objects.create(
            user=user_2,
            character=eve_char_2,
            owner_hash="2",
        )
        member_2 = Member.objects.create(
            main_character=eve_char_2,
            first_main_character=eve_char_2,
        )

        Character.objects.create(
            eve_character=eve_char_2,
            member=member_2,
        )

        user_3 = AuthUtils.create_user("Character_3")

        eve_char_3 = EveCharacter.objects.create(
            character_id=3,
            character_name="Character 3",
            corporation_id=1,
            corporation_name="Corp",
            corporation_ticker="CORP",
        )

        user_3.profile.main_character = eve_char_3
        user_3.profile.save()

        CharacterOwnership.objects.create(
            user=user_3,
            character=eve_char_3,
            owner_hash="3",
        )
        member_3 = Member.objects.create(
            main_character=eve_char_3,
            first_main_character=eve_char_3,
            awarded_title=self.title,
        )

        Character.objects.create(
            eve_character=eve_char_3,
            member=member_3,
        )

        AuthUtils.connect_signals()

        test_filter = TitleFilter.objects.create(
            description="Test Filter",
        )
        test_filter.awarded_titles.add(self.title)

        ret = test_filter.audit_filter(
            [
                self.user.pk,
                user_2.pk,
                user_3.pk,
            ]
        )

        self.assertTrue(ret[self.user.pk]["check"])
        self.assertFalse(ret[user_2.pk]["check"])
        self.assertTrue(ret[user_3.pk]["check"])

    def test_audit_filter_applied_single_member(self):
        member = Member.objects.create(
            main_character=self.eve_char,
            first_main_character=self.eve_char,
            awarded_title=self.title,
        )
        Character.objects.create(
            eve_character=self.eve_char,
            member=member,
            applied_title=self.title,
        )

        test_filter = TitleFilter.objects.create(
            description="Test Filter",
        )
        test_filter.awarded_titles.add(self.title)
        test_filter.applied_titles.add(self.title)

        ret = test_filter.audit_filter([self.user.pk])

        self.assertTrue(ret[self.user.pk]["check"])

    def test_audit_filter_applied_multi_member(self):
        member = Member.objects.create(
            main_character=self.eve_char,
            first_main_character=self.eve_char,
            awarded_title=self.title,
        )
        Character.objects.create(
            eve_character=self.eve_char,
            member=member,
            applied_title=self.title,
        )

        AuthUtils.disconnect_signals()

        user_2 = AuthUtils.create_user("Character_2")

        eve_char_2 = EveCharacter.objects.create(
            character_id=2,
            character_name="Character 2",
            corporation_id=1,
            corporation_name="Corp",
            corporation_ticker="CORP",
        )

        user_2.profile.main_character = eve_char_2
        user_2.profile.save()

        CharacterOwnership.objects.create(
            user=user_2,
            character=eve_char_2,
            owner_hash="2",
        )
        member_2 = Member.objects.create(
            main_character=eve_char_2,
            first_main_character=eve_char_2,
            awarded_title=self.title,
        )

        Character.objects.create(
            eve_character=eve_char_2,
            member=member_2,
            applied_title=self.title,
        )

        user_3 = AuthUtils.create_user("Character_3")

        eve_char_3 = EveCharacter.objects.create(
            character_id=3,
            character_name="Character 3",
            corporation_id=1,
            corporation_name="Corp",
            corporation_ticker="CORP",
        )

        user_3.profile.main_character = eve_char_3
        user_3.profile.save()

        CharacterOwnership.objects.create(
            user=user_3,
            character=eve_char_3,
            owner_hash="3",
        )
        member_3 = Member.objects.create(
            main_character=eve_char_3,
            first_main_character=eve_char_3,
            awarded_title=self.title,
        )

        Character.objects.create(
            eve_character=eve_char_3,
            member=member_3,
        )

        AuthUtils.connect_signals()

        test_filter = TitleFilter.objects.create(
            description="Test Filter",
        )
        test_filter.awarded_titles.add(self.title)
        test_filter.applied_titles.add(self.title)

        ret = test_filter.audit_filter(
            [
                self.user.pk,
                user_2.pk,
                user_3.pk,
            ]
        )

        self.assertTrue(ret[self.user.pk]["check"])
        self.assertTrue(ret[user_2.pk]["check"])
        self.assertFalse(ret[user_3.pk]["check"])
