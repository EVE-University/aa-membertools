# Django
from django.contrib.auth.models import Group
from django.test import TestCase

# Alliance Auth
from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
from allianceauth.tests.auth_utils import AuthUtils

from ..models import (
    Application,
    ApplicationForm,
    ApplicationQuestion,
    ApplicationTitle,
    Character,
    Member,
)


class TestModelAppForm(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.auditor_group = Group.objects.create(name="Auditor")
        cls.recruiter_group = Group.objects.create(name="Recruiter")
        cls.manager_group = Group.objects.create(name="Manager")

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
        cls.corp_app_form.auditor_groups.add(cls.auditor_group)
        cls.corp_app_form.recruiter_groups.add(cls.recruiter_group)
        cls.corp_app_form.manager_groups.add(cls.manager_group)

        cls.title = ApplicationTitle.objects.create(name="Title 1", priority=1)
        cls.title_app_form = ApplicationForm.objects.create(
            corp=cls.corp,
            title=cls.title,
        )
        cls.title_app_form.questions.add(
            ApplicationQuestion.objects.create(
                title="A Title Question",
                help_text="A text question",
            )
        )

        return super().setUpTestData()

    def test_app_form_superuser_is_all_roles(self):
        user = AuthUtils.create_user("Superuser", disconnect_signals=True)
        user.is_superuser = True
        user.save()

        self.assertTrue(self.corp_app_form.is_user_auditor(user))
        self.assertTrue(self.corp_app_form.is_user_recruiter(user))
        self.assertTrue(self.corp_app_form.is_user_manager(user))

    def test_app_form_is_user_auditor(self):
        user = AuthUtils.create_user("Auditor_Officer", disconnect_signals=True)
        user.groups.add(self.auditor_group)
        user.save()

        self.assertTrue(self.corp_app_form.is_user_auditor(user))
        self.assertFalse(self.corp_app_form.is_user_recruiter(user))
        self.assertFalse(self.corp_app_form.is_user_manager(user))

    def test_app_form_is_user_recruiter(self):
        user = AuthUtils.create_user("Recruiter_Officer", disconnect_signals=True)
        user.groups.add(self.recruiter_group)
        user.save()

        self.assertFalse(self.corp_app_form.is_user_auditor(user))
        self.assertTrue(self.corp_app_form.is_user_recruiter(user))
        self.assertFalse(self.corp_app_form.is_user_manager(user))

    def test_app_form_is_user_manager(self):
        user = AuthUtils.create_user("Manager_Officer", disconnect_signals=True)
        user.groups.add(self.manager_group)
        user.save()

        self.assertFalse(self.corp_app_form.is_user_auditor(user))
        self.assertFalse(self.corp_app_form.is_user_recruiter(user))
        self.assertTrue(self.corp_app_form.is_user_manager(user))

    def test_app_form_is_available_to_non_member(self):
        char = EveCharacter.objects.create(
            character_id=1,
            character_name="Applicant 1",
            corporation_id=1,
            corporation_name="Corp",
            corporation_ticker="CORP",
        )

        user = AuthUtils.create_user("Applicant_1", disconnect_signals=True)

        AuthUtils.disconnect_signals()
        user.profile.main_character = char
        user.profile.save()

        CharacterOwnership.objects.create(
            user=user,
            character=char,
            owner_hash="1",
        )
        AuthUtils.connect_signals()

        self.assertTrue(self.corp_app_form.user_has_eligible_chars(user))

    def test_app_form_is_not_available_to_member(self):
        char = EveCharacter.objects.create(
            character_id=1,
            character_name="Member 1",
            corporation_id=self.corp.corporation_id,
            corporation_name=self.corp.corporation_name,
            corporation_ticker=self.corp.corporation_ticker,
        )

        user = AuthUtils.create_user("Member_1", disconnect_signals=True)

        AuthUtils.disconnect_signals()
        user.profile.main_character = char
        user.profile.save()

        CharacterOwnership.objects.create(
            user=user,
            character=char,
            owner_hash="1",
        )
        AuthUtils.connect_signals()

        self.assertFalse(self.corp_app_form.user_has_eligible_chars(user))

    def test_app_form_is_available_to_alt_of_member(self):
        char = EveCharacter.objects.create(
            character_id=1,
            character_name="Member 1",
            corporation_id=self.corp.corporation_id,
            corporation_name=self.corp.corporation_name,
            corporation_ticker=self.corp.corporation_ticker,
        )

        alt = EveCharacter.objects.create(
            character_id=2,
            character_name="Alt 1",
            corporation_id=1,
            corporation_name="Corp",
            corporation_ticker="CORP",
        )

        user = AuthUtils.create_user("Member_1", disconnect_signals=True)

        AuthUtils.disconnect_signals()
        user.profile.main_character = char
        user.profile.save()

        CharacterOwnership.objects.create(
            user=user,
            character=char,
            owner_hash="1",
        )
        CharacterOwnership.objects.create(
            user=user,
            character=alt,
            owner_hash="2",
        )
        AuthUtils.connect_signals()

        self.assertEqual(self.corp_app_form.get_user_eligible_chars(user), [alt])

    def test_app_form_is_not_available_to_member_plus_member_alt(self):
        char = EveCharacter.objects.create(
            character_id=1,
            character_name="Member 1",
            corporation_id=self.corp.corporation_id,
            corporation_name=self.corp.corporation_name,
            corporation_ticker=self.corp.corporation_ticker,
        )

        alt = EveCharacter.objects.create(
            character_id=2,
            character_name="Alt 1",
            corporation_id=self.corp.corporation_id,
            corporation_name=self.corp.corporation_name,
            corporation_ticker=self.corp.corporation_ticker,
        )

        user = AuthUtils.create_user("Member_1", disconnect_signals=True)

        AuthUtils.disconnect_signals()
        user.profile.main_character = char
        user.profile.save()

        CharacterOwnership.objects.create(
            user=user,
            character=char,
            owner_hash="1",
        )
        CharacterOwnership.objects.create(
            user=user,
            character=alt,
            owner_hash="2",
        )
        AuthUtils.connect_signals()

        self.assertEqual(self.corp_app_form.get_user_eligible_chars(user), [])

    def test_app_form_is_not_available_to_no_main(self):
        char = EveCharacter.objects.create(
            character_id=1,
            character_name="Applicant 1",
            corporation_id=1,
            corporation_name="Corp",
            corporation_ticker="CORP",
        )

        user = AuthUtils.create_user("Applicant_1", disconnect_signals=True)

        AuthUtils.disconnect_signals()

        CharacterOwnership.objects.create(
            user=user,
            character=char,
            owner_hash="1",
        )
        AuthUtils.connect_signals()

        self.assertEqual(self.corp_app_form.get_user_eligible_chars(user), [])

    def test_app_form_is_available_to_previous_applicant(self):
        eve_char = EveCharacter.objects.create(
            character_id=1,
            character_name="Applicant 1",
            corporation_id=1,
            corporation_name="Corp",
            corporation_ticker="CORP",
        )

        user = AuthUtils.create_user("Applicant_1", disconnect_signals=True)

        AuthUtils.disconnect_signals()
        user.profile.main_character = eve_char
        user.profile.save()

        CharacterOwnership.objects.create(
            user=user,
            character=eve_char,
            owner_hash="1",
        )
        AuthUtils.connect_signals()

        member = Member.objects.create(
            first_main_character=eve_char,
            main_character=eve_char,
        )

        char = Character.objects.create(
            eve_character=eve_char,
            member=member,
        )

        Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=eve_char,
            reviewer=eve_char,
            decision_by=eve_char,
            status=Application.STATUS_CLOSED,
            decision=Application.DECISION_ACCEPT,
        )

        self.assertTrue(self.corp_app_form.user_has_eligible_chars(user))

    def test_app_form_is_not_available_to_recent_applicant(self):
        eve_char = EveCharacter.objects.create(
            character_id=1,
            character_name="Applicant 1",
            corporation_id=1,
            corporation_name="Corp",
            corporation_ticker="CORP",
        )

        user = AuthUtils.create_user("Applicant_1", disconnect_signals=True)

        AuthUtils.disconnect_signals()
        user.profile.main_character = eve_char
        user.profile.save()

        CharacterOwnership.objects.create(
            user=user,
            character=eve_char,
            owner_hash="1",
        )
        AuthUtils.connect_signals()

        member = Member.objects.create(
            first_main_character=eve_char,
            main_character=eve_char,
        )

        char = Character.objects.create(
            eve_character=eve_char,
            member=member,
        )

        Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=eve_char,
            reviewer=eve_char,
            decision_by=eve_char,
            status=Application.STATUS_PROCESSED,
            decision=Application.DECISION_ACCEPT,
        )

        self.assertFalse(self.corp_app_form.user_has_eligible_chars(user))

    def test_app_form_is_not_available_to_current_applicant(self):
        eve_char = EveCharacter.objects.create(
            character_id=1,
            character_name="Applicant 1",
            corporation_id=1,
            corporation_name="Corp",
            corporation_ticker="CORP",
        )

        user = AuthUtils.create_user("Applicant_1", disconnect_signals=True)

        AuthUtils.disconnect_signals()
        user.profile.main_character = eve_char
        user.profile.save()

        CharacterOwnership.objects.create(
            user=user,
            character=eve_char,
            owner_hash="1",
        )
        AuthUtils.connect_signals()

        member = Member.objects.create(
            first_main_character=eve_char,
            main_character=eve_char,
        )

        char = Character.objects.create(
            eve_character=eve_char,
            member=member,
        )

        Application.objects.create(
            form=self.corp_app_form,
            character=char,
            eve_character=eve_char,
            status=Application.STATUS_NEW,
            decision=Application.DECISION_PENDING,
        )

        self.assertFalse(self.corp_app_form.user_has_eligible_chars(user))

    def test_title_form_is_available_for_member(self):
        char = EveCharacter.objects.create(
            character_id=1,
            character_name="Member 1",
            corporation_id=self.corp.corporation_id,
            corporation_name=self.corp.corporation_name,
            corporation_ticker=self.corp.corporation_ticker,
        )

        user = AuthUtils.create_user("Applicant_1", disconnect_signals=True)

        AuthUtils.disconnect_signals()
        user.profile.main_character = char
        user.profile.save()

        CharacterOwnership.objects.create(
            user=user,
            character=char,
            owner_hash="1",
        )
        AuthUtils.connect_signals()

        self.assertEqual(
            self.title_app_form.get_user_eligible_chars(user),
            [char],
        )

    def test_title_require_awarded_none_with_none(self):
        self.title_app_form.require_awarded = True

        eve_char = EveCharacter.objects.create(
            character_id=1,
            character_name="Member 1",
            corporation_id=self.corp.corporation_id,
            corporation_name=self.corp.corporation_name,
            corporation_ticker=self.corp.corporation_ticker,
        )

        member = Member.objects.create(
            first_main_character=eve_char, main_character=eve_char
        )

        Character.objects.create(
            eve_character=eve_char,
            member=member,
        )

        user = AuthUtils.create_user("Applicant_1", disconnect_signals=True)

        AuthUtils.disconnect_signals()
        user.profile.main_character = eve_char
        user.profile.save()

        CharacterOwnership.objects.create(
            user=user,
            character=eve_char,
            owner_hash="1",
        )
        AuthUtils.connect_signals()

        self.assertEqual(
            self.title_app_form.get_user_eligible_chars(user),
            [eve_char],
        )

    def test_title_require_awarded_title_with_title(self):
        self.title_app_form.require_awarded = True
        self.title_app_form.allow_awarded.add(self.title)

        eve_char = EveCharacter.objects.create(
            character_id=1,
            character_name="Member 1",
            corporation_id=self.corp.corporation_id,
            corporation_name=self.corp.corporation_name,
            corporation_ticker=self.corp.corporation_ticker,
        )

        member = Member.objects.create(
            first_main_character=eve_char,
            main_character=eve_char,
            awarded_title=self.title,
        )

        Character.objects.create(
            eve_character=eve_char,
            member=member,
        )

        user = AuthUtils.create_user("Applicant_1", disconnect_signals=True)

        AuthUtils.disconnect_signals()
        user.profile.main_character = eve_char
        user.profile.save()

        CharacterOwnership.objects.create(
            user=user,
            character=eve_char,
            owner_hash="1",
        )
        AuthUtils.connect_signals()

        self.assertEqual(
            self.title_app_form.get_user_eligible_chars(user),
            [eve_char],
        )

    def test_title_require_awarded_title_without_title(self):
        self.title_app_form.require_awarded = True
        self.title_app_form.allow_awarded.add(self.title)

        eve_char = EveCharacter.objects.create(
            character_id=1,
            character_name="Member 1",
            corporation_id=self.corp.corporation_id,
            corporation_name=self.corp.corporation_name,
            corporation_ticker=self.corp.corporation_ticker,
        )

        member = Member.objects.create(
            first_main_character=eve_char,
            main_character=eve_char,
        )

        Character.objects.create(
            eve_character=eve_char,
            member=member,
        )

        user = AuthUtils.create_user("Applicant_1", disconnect_signals=True)

        AuthUtils.disconnect_signals()
        user.profile.main_character = eve_char
        user.profile.save()

        CharacterOwnership.objects.create(
            user=user,
            character=eve_char,
            owner_hash="1",
        )
        AuthUtils.connect_signals()

        self.assertEqual(
            self.title_app_form.get_user_eligible_chars(user),
            [],
        )

    def test_title_require_awarded_title_with_title_applied(self):
        self.title_app_form.require_awarded = True
        self.title_app_form.allow_awarded.add(self.title)

        eve_char = EveCharacter.objects.create(
            character_id=1,
            character_name="Member 1",
            corporation_id=self.corp.corporation_id,
            corporation_name=self.corp.corporation_name,
            corporation_ticker=self.corp.corporation_ticker,
        )

        member = Member.objects.create(
            first_main_character=eve_char,
            main_character=eve_char,
            awarded_title=self.title,
        )

        Character.objects.create(
            eve_character=eve_char,
            member=member,
            applied_title=self.title,
        )

        user = AuthUtils.create_user("Applicant_1", disconnect_signals=True)

        AuthUtils.disconnect_signals()
        user.profile.main_character = eve_char
        user.profile.save()

        CharacterOwnership.objects.create(
            user=user,
            character=eve_char,
            owner_hash="1",
        )
        AuthUtils.connect_signals()

        self.assertEqual(
            self.title_app_form.get_user_eligible_chars(user),
            [],
        )

    def test_title_require_applied_none_with_none(self):
        self.title_app_form.require_applied = True

        eve_char = EveCharacter.objects.create(
            character_id=1,
            character_name="Member 1",
            corporation_id=self.corp.corporation_id,
            corporation_name=self.corp.corporation_name,
            corporation_ticker=self.corp.corporation_ticker,
        )

        member = Member.objects.create(
            first_main_character=eve_char,
            main_character=eve_char,
            awarded_title=self.title,
        )

        Character.objects.create(
            eve_character=eve_char,
            member=member,
        )

        user = AuthUtils.create_user("Applicant_1", disconnect_signals=True)

        AuthUtils.disconnect_signals()
        user.profile.main_character = eve_char
        user.profile.save()

        CharacterOwnership.objects.create(
            user=user,
            character=eve_char,
            owner_hash="1",
        )
        AuthUtils.connect_signals()

        self.assertEqual(
            self.title_app_form.get_user_eligible_chars(user),
            [eve_char],
        )

    def test_title_require_applied_title_with_title(self):
        self.title_app_form.require_applied = True
        self.title_app_form.allow_applied.add(self.title)

        eve_char = EveCharacter.objects.create(
            character_id=1,
            character_name="Member 1",
            corporation_id=self.corp.corporation_id,
            corporation_name=self.corp.corporation_name,
            corporation_ticker=self.corp.corporation_ticker,
        )

        member = Member.objects.create(
            first_main_character=eve_char,
            main_character=eve_char,
            awarded_title=self.title,
        )

        Character.objects.create(
            eve_character=eve_char,
            member=member,
            applied_title=self.title,
        )

        user = AuthUtils.create_user("Applicant_1", disconnect_signals=True)

        AuthUtils.disconnect_signals()
        user.profile.main_character = eve_char
        user.profile.save()

        CharacterOwnership.objects.create(
            user=user,
            character=eve_char,
            owner_hash="1",
        )
        AuthUtils.connect_signals()

        self.assertEqual(
            self.title_app_form.get_user_eligible_chars(user),
            [],
        )

    def test_title_require_applied_title_without_title(self):
        self.title_app_form.require_applied = True
        self.title_app_form.allow_applied.add(self.title)

        eve_char = EveCharacter.objects.create(
            character_id=1,
            character_name="Member 1",
            corporation_id=self.corp.corporation_id,
            corporation_name=self.corp.corporation_name,
            corporation_ticker=self.corp.corporation_ticker,
        )

        member = Member.objects.create(
            first_main_character=eve_char,
            main_character=eve_char,
            awarded_title=self.title,
        )

        Character.objects.create(
            eve_character=eve_char,
            member=member,
        )

        user = AuthUtils.create_user("Applicant_1", disconnect_signals=True)

        AuthUtils.disconnect_signals()
        user.profile.main_character = eve_char
        user.profile.save()

        CharacterOwnership.objects.create(
            user=user,
            character=eve_char,
            owner_hash="1",
        )
        AuthUtils.connect_signals()

        self.assertEqual(
            self.title_app_form.get_user_eligible_chars(user),
            [],
        )

    def test_title_require_applied_title_with_title_applied(self):
        self.title_app_form.require_applied = True
        self.title_app_form.allow_applied.add(self.title)

        eve_char = EveCharacter.objects.create(
            character_id=1,
            character_name="Member 1",
            corporation_id=self.corp.corporation_id,
            corporation_name=self.corp.corporation_name,
            corporation_ticker=self.corp.corporation_ticker,
        )

        member = Member.objects.create(
            first_main_character=eve_char,
            main_character=eve_char,
            awarded_title=self.title,
        )

        Character.objects.create(
            eve_character=eve_char,
            member=member,
            applied_title=self.title,
        )

        user = AuthUtils.create_user("Applicant_1", disconnect_signals=True)

        AuthUtils.disconnect_signals()
        user.profile.main_character = eve_char
        user.profile.save()

        CharacterOwnership.objects.create(
            user=user,
            character=eve_char,
            owner_hash="1",
        )
        AuthUtils.connect_signals()

        self.assertEqual(
            self.title_app_form.get_user_eligible_chars(user),
            [],
        )

    def test_title_require_applied_and_awarded_none_without_title(self):
        self.title_app_form.require_awarded = True
        self.title_app_form.require_applied = True

        eve_char = EveCharacter.objects.create(
            character_id=1,
            character_name="Member 1",
            corporation_id=self.corp.corporation_id,
            corporation_name=self.corp.corporation_name,
            corporation_ticker=self.corp.corporation_ticker,
        )

        member = Member.objects.create(
            first_main_character=eve_char,
            main_character=eve_char,
        )

        Character.objects.create(
            eve_character=eve_char,
            member=member,
        )

        user = AuthUtils.create_user("Applicant_1", disconnect_signals=True)

        AuthUtils.disconnect_signals()
        user.profile.main_character = eve_char
        user.profile.save()

        CharacterOwnership.objects.create(
            user=user,
            character=eve_char,
            owner_hash="1",
        )
        AuthUtils.connect_signals()

        self.assertEqual(
            self.title_app_form.get_user_eligible_chars(user),
            [eve_char],
        )

    def test_title_require_applied_and_awarded_title_without_title(self):
        self.title_app_form.require_awarded = True
        self.title_app_form.require_applied = True
        self.title_app_form.allow_awarded.add(self.title)
        self.title_app_form.allow_applied.add(self.title)

        eve_char = EveCharacter.objects.create(
            character_id=1,
            character_name="Member 1",
            corporation_id=self.corp.corporation_id,
            corporation_name=self.corp.corporation_name,
            corporation_ticker=self.corp.corporation_ticker,
        )

        member = Member.objects.create(
            first_main_character=eve_char,
            main_character=eve_char,
        )

        Character.objects.create(
            eve_character=eve_char,
            member=member,
        )

        user = AuthUtils.create_user("Applicant_1", disconnect_signals=True)

        AuthUtils.disconnect_signals()
        user.profile.main_character = eve_char
        user.profile.save()

        CharacterOwnership.objects.create(
            user=user,
            character=eve_char,
            owner_hash="1",
        )
        AuthUtils.connect_signals()

        self.assertEqual(
            self.title_app_form.get_user_eligible_chars(user),
            [],
        )

    def test_title_require_awarded_title_and_applied_none_main_alt_without_applied(
        self,
    ):
        self.title_app_form.require_awarded = True
        self.title_app_form.require_applied = True
        self.title_app_form.allow_awarded.add(self.title)

        eve_char = EveCharacter.objects.create(
            character_id=1,
            character_name="Member 1",
            corporation_id=self.corp.corporation_id,
            corporation_name=self.corp.corporation_name,
            corporation_ticker=self.corp.corporation_ticker,
        )

        alt_eve_char = EveCharacter.objects.create(
            character_id=2,
            character_name="Alt 1",
            corporation_id=self.corp.corporation_id,
            corporation_name=self.corp.corporation_name,
            corporation_ticker=self.corp.corporation_ticker,
        )

        member = Member.objects.create(
            first_main_character=eve_char,
            main_character=eve_char,
            awarded_title=self.title,
        )

        Character.objects.create(
            eve_character=eve_char,
            member=member,
        )

        Character.objects.create(
            eve_character=alt_eve_char,
            member=member,
        )

        user = AuthUtils.create_user("Member_1", disconnect_signals=True)

        AuthUtils.disconnect_signals()
        user.profile.main_character = eve_char
        user.profile.save()

        CharacterOwnership.objects.create(
            user=user,
            character=eve_char,
            owner_hash="1",
        )
        CharacterOwnership.objects.create(
            user=user,
            character=alt_eve_char,
            owner_hash="2",
        )

        AuthUtils.connect_signals()

        self.assertCountEqual(
            self.title_app_form.get_user_eligible_chars(user),
            [eve_char, alt_eve_char],
        )

    def test_title_require_awarded_title_and_applied_title_main_with_alt_without_applied(
        self,
    ):
        self.title_app_form.require_awarded = True
        self.title_app_form.require_applied = True
        self.title_app_form.allow_awarded.add(self.title)
        self.title_app_form.allow_applied.add(self.title)

        eve_char = EveCharacter.objects.create(
            character_id=1,
            character_name="Member 1",
            corporation_id=self.corp.corporation_id,
            corporation_name=self.corp.corporation_name,
            corporation_ticker=self.corp.corporation_ticker,
        )

        alt_eve_char = EveCharacter.objects.create(
            character_id=2,
            character_name="Alt 1",
            corporation_id=self.corp.corporation_id,
            corporation_name=self.corp.corporation_name,
            corporation_ticker=self.corp.corporation_ticker,
        )

        member = Member.objects.create(
            first_main_character=eve_char,
            main_character=eve_char,
            awarded_title=self.title,
        )

        Character.objects.create(
            eve_character=eve_char,
            member=member,
            applied_title=self.title,
        )

        Character.objects.create(
            eve_character=alt_eve_char,
            member=member,
        )

        user = AuthUtils.create_user("Member_1", disconnect_signals=True)

        AuthUtils.disconnect_signals()
        user.profile.main_character = eve_char
        user.profile.save()

        CharacterOwnership.objects.create(
            user=user,
            character=eve_char,
            owner_hash="1",
        )
        CharacterOwnership.objects.create(
            user=user,
            character=alt_eve_char,
            owner_hash="2",
        )

        AuthUtils.connect_signals()

        self.assertEqual(
            self.title_app_form.get_user_eligible_chars(user),
            [],
        )

    def test_title_next_title_available_for_main_current_title_for_alt(
        self,
    ):
        self.title_app_form.require_awarded = True
        self.title_app_form.require_applied = True
        self.title_app_form.allow_awarded.add(self.title)

        next_title = ApplicationTitle.objects.create(name="Title 2", priority=2)
        next_title_app_form = ApplicationForm.objects.create(
            corp=self.corp,
            title=next_title,
        )
        next_title_app_form.questions.add(
            ApplicationQuestion.objects.create(
                title="A Title Question",
                help_text="A text question",
            )
        )
        next_title_app_form.allow_awarded.add(self.title)
        next_title_app_form.allow_awarded.add(next_title)
        next_title_app_form.allow_applied.add(self.title)

        eve_char = EveCharacter.objects.create(
            character_id=1,
            character_name="Member 1",
            corporation_id=self.corp.corporation_id,
            corporation_name=self.corp.corporation_name,
            corporation_ticker=self.corp.corporation_ticker,
        )

        alt_eve_char = EveCharacter.objects.create(
            character_id=2,
            character_name="Alt 1",
            corporation_id=self.corp.corporation_id,
            corporation_name=self.corp.corporation_name,
            corporation_ticker=self.corp.corporation_ticker,
        )

        member = Member.objects.create(
            first_main_character=eve_char,
            main_character=eve_char,
            awarded_title=self.title,
        )

        Character.objects.create(
            eve_character=eve_char,
            member=member,
            applied_title=self.title,
        )

        Character.objects.create(
            eve_character=alt_eve_char,
            member=member,
        )

        user = AuthUtils.create_user("Member_1", disconnect_signals=True)

        AuthUtils.disconnect_signals()
        user.profile.main_character = eve_char
        user.profile.save()

        CharacterOwnership.objects.create(
            user=user,
            character=eve_char,
            owner_hash="1",
        )
        CharacterOwnership.objects.create(
            user=user,
            character=alt_eve_char,
            owner_hash="2",
        )

        AuthUtils.connect_signals()

        self.assertEqual(
            next_title_app_form.get_user_eligible_chars(user),
            [eve_char],
        )

        self.assertEqual(
            self.title_app_form.get_user_eligible_chars(user),
            [alt_eve_char],
        )

    def test_title_require_awarded_title_with_title_no_character_record(self):
        self.title_app_form.require_awarded = True
        self.title_app_form.allow_awarded.add(self.title)

        eve_char = EveCharacter.objects.create(
            character_id=1,
            character_name="Member 1",
            corporation_id=self.corp.corporation_id,
            corporation_name=self.corp.corporation_name,
            corporation_ticker=self.corp.corporation_ticker,
        )

        Member.objects.create(
            first_main_character=eve_char,
            main_character=eve_char,
            awarded_title=self.title,
        )

        user = AuthUtils.create_user("Applicant_1", disconnect_signals=True)

        AuthUtils.disconnect_signals()
        user.profile.main_character = eve_char
        user.profile.save()

        CharacterOwnership.objects.create(
            user=user,
            character=eve_char,
            owner_hash="1",
        )
        AuthUtils.connect_signals()

        self.assertEqual(
            self.title_app_form.get_user_eligible_chars(user),
            [eve_char],
        )
