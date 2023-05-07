# Django
from django.contrib.auth.models import Group
from django.test import TestCase

# Alliance Auth
from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
from allianceauth.tests.auth_utils import AuthUtils

from ..models import Application, ApplicationForm, ApplicationQuestion, Character


class TestManagerApp(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.recruiter_group = Group.objects.create(name="Recruiter")

        cls.corp = EveCorporationInfo.objects.create(
            corporation_id=10,
            corporation_name="Join Me",
            corporation_ticker="JOIN",
            member_count=20,
        )
        cls.app_form_question = ApplicationQuestion.objects.create(
            title="Text Question",
            help_text="A text question",
        )
        cls.corp_app_form = ApplicationForm.objects.create(corp=cls.corp)
        cls.corp_app_form.questions.add(cls.app_form_question)
        cls.corp_app_form.recruiter_groups.add(cls.recruiter_group)

        # Hidden corp
        cls.hidden_recruiter_group = Group.objects.create(name="Hidden Recruiter")

        cls.hidden_corp = EveCorporationInfo.objects.create(
            corporation_id=20,
            corporation_name="Hidden Corp Village",
            corporation_ticker="HIDE",
            member_count=10,
        )
        cls.hidden_corp_app_form = ApplicationForm.objects.create(corp=cls.hidden_corp)
        cls.hidden_corp_app_form.questions.add(cls.app_form_question)
        cls.hidden_corp_app_form.recruiter_groups.add(cls.hidden_recruiter_group)

        # Make some users/mains
        AuthUtils.disconnect_signals()

        cls.officer = AuthUtils.create_user("Recruitment_Officer")
        cls.officer.groups.add(cls.recruiter_group)

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

        cls.applicant_1 = AuthUtils.create_user("Applicant_1")

        cls.applicant_1_eve_char = EveCharacter.objects.create(
            character_id=1,
            character_name="Applicant 1",
            corporation_id=1,
            corporation_name="Corp",
            corporation_ticker="CORP",
        )

        cls.applicant_1.profile.main_character = cls.applicant_1_eve_char
        cls.applicant_1.profile.save()

        CharacterOwnership.objects.create(
            user=cls.applicant_1,
            character=cls.applicant_1_eve_char,
            owner_hash="1",
        )

        cls.applicant_2 = AuthUtils.create_user("Applicant_2")

        cls.applicant_2_eve_char = EveCharacter.objects.create(
            character_id=2,
            character_name="Applicant 2",
            corporation_id=1,
            corporation_name="Corp",
            corporation_ticker="CORP",
        )

        cls.applicant_2.profile.main_character = cls.applicant_2_eve_char
        cls.applicant_2.profile.save()

        CharacterOwnership.objects.create(
            user=cls.applicant_2,
            character=cls.applicant_2_eve_char,
            owner_hash="2",
        )

        AuthUtils.connect_signals()

        return super().setUpTestData()

    def test_recent_processed_apps_for_user(self):
        char = Character.objects.create(
            eve_character=self.applicant_1_eve_char,
            member=None,
        )

        Application.objects.create(
            form=self.corp_app_form,
            eve_character=self.applicant_1_eve_char,
            character=char,
            status=Application.STATUS_PROCESSED,
            decision=Application.DECISION_ACCEPT,
            decision_by=self.officer_eve_char,
        )

        Application.objects.create(
            form=self.corp_app_form,
            eve_character=self.applicant_1_eve_char,
            character=char,
            status=Application.STATUS_WAIT,
        )

        self.assertEqual(
            Application.objects.recent_finished_apps_count_for_user(self.applicant_1), 1
        )

        self.assertEqual(
            Application.objects.recent_finished_apps_count_for_user(self.applicant_2), 0
        )

    def test_admin_new_app_count_single(self):
        char = Character.objects.create(
            eve_character=self.applicant_1_eve_char,
            member=None,
        )

        Application.objects.create(
            form=self.corp_app_form,
            eve_character=self.applicant_1_eve_char,
            character=char,
            status=Application.STATUS_NEW,
        )

        self.assertEqual(
            Application.objects.new_application_count_for_admin_user(self.officer), 1
        )

    def test_admin_new_app_count_multi(self):
        char = Character.objects.create(
            eve_character=self.applicant_1_eve_char,
            member=None,
        )

        char_2 = Character.objects.create(
            eve_character=self.applicant_2_eve_char,
            member=None,
        )

        Application.objects.create(
            form=self.corp_app_form,
            eve_character=self.applicant_1_eve_char,
            character=char,
            status=Application.STATUS_NEW,
        )

        Application.objects.create(
            form=self.corp_app_form,
            eve_character=self.applicant_2_eve_char,
            character=char_2,
            status=Application.STATUS_NEW,
        )

        Application.objects.create(
            form=self.hidden_corp_app_form,
            eve_character=self.applicant_1_eve_char,
            character=char,
            status=Application.STATUS_NEW,
        )

        self.assertEqual(
            Application.objects.new_application_count_for_admin_user(self.officer), 2
        )

    def test_admin_wait_app_count_single(self):
        char = Character.objects.create(
            eve_character=self.applicant_1_eve_char,
            member=None,
        )

        Application.objects.create(
            form=self.corp_app_form,
            eve_character=self.applicant_1_eve_char,
            character=char,
            status=Application.STATUS_WAIT,
        )

        self.assertEqual(
            Application.objects.wait_application_count_for_admin_user(self.officer), 1
        )

    def test_admin_wait_app_count_multi(self):
        char = Character.objects.create(
            eve_character=self.applicant_1_eve_char,
            member=None,
        )

        char_2 = Character.objects.create(
            eve_character=self.applicant_2_eve_char,
            member=None,
        )

        Application.objects.create(
            form=self.corp_app_form,
            eve_character=self.applicant_1_eve_char,
            character=char,
            status=Application.STATUS_WAIT,
        )

        Application.objects.create(
            form=self.corp_app_form,
            eve_character=self.applicant_2_eve_char,
            character=char_2,
            status=Application.STATUS_WAIT,
        )

        Application.objects.create(
            form=self.hidden_corp_app_form,
            eve_character=self.applicant_1_eve_char,
            character=char,
            status=Application.STATUS_WAIT,
        )

        self.assertEqual(
            Application.objects.wait_application_count_for_admin_user(self.officer), 2
        )
