# Django
from django.contrib.auth.models import Group
from django.test import TestCase

# Alliance Auth
from allianceauth.eveonline.models import EveCorporationInfo
from allianceauth.tests.auth_utils import AuthUtils

from ..models import ApplicationForm, ApplicationQuestion


class TestManagerAppForm(TestCase):
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
        cls.app_form_question = ApplicationQuestion.objects.create(
            title="Text Question",
            help_text="A text question",
        )
        cls.corp_app_form = ApplicationForm.objects.create(corp=cls.corp)
        cls.corp_app_form.questions.add(cls.app_form_question)
        cls.corp_app_form.auditor_groups.add(cls.auditor_group)
        cls.corp_app_form.recruiter_groups.add(cls.recruiter_group)
        cls.corp_app_form.manager_groups.add(cls.manager_group)

        # Hidden corp
        cls.hidden_auditor_group = Group.objects.create(name="Hidden Auditor")
        cls.hidden_recruiter_group = Group.objects.create(name="Hidden Recruiter")
        cls.hidden_manager_group = Group.objects.create(name="Hidden Manager")

        cls.hidden_corp = EveCorporationInfo.objects.create(
            corporation_id=20,
            corporation_name="Hidden Corp Village",
            corporation_ticker="HIDE",
            member_count=10,
        )
        cls.hidden_corp_app_form = ApplicationForm.objects.create(corp=cls.hidden_corp)
        cls.hidden_corp_app_form.questions.add(cls.app_form_question)
        cls.hidden_corp_app_form.auditor_groups.add(cls.hidden_auditor_group)
        cls.hidden_corp_app_form.recruiter_groups.add(cls.hidden_recruiter_group)
        cls.hidden_corp_app_form.manager_groups.add(cls.hidden_manager_group)

        return super().setUpTestData()

    def test_get_forms_for_superuser(self):
        user = AuthUtils.create_user("Superuser", disconnect_signals=True)
        user.is_superuser = True
        user.save()

        self.assertCountEqual(
            list(ApplicationForm.objects.get_forms_for_user(user)),
            [self.corp_app_form, self.hidden_corp_app_form],
        )

    def test_get_forms_for_audit_user(self):
        user = AuthUtils.create_user("Auditor_Officer", disconnect_signals=True)
        user.groups.add(self.auditor_group)

        forms = ApplicationForm.objects.get_forms_for_user(user)
        self.assertCountEqual(
            list(ApplicationForm.objects.get_forms_for_user(user)),
            [self.corp_app_form],
        )

        self.assertTrue(forms[0].is_auditor)
        self.assertFalse(forms[0].is_recruiter)
        self.assertFalse(forms[0].is_manager)

    def test_get_forms_for_mixed_user(self):
        user = AuthUtils.create_user("Auditor_Officer", disconnect_signals=True)
        user.groups.add(self.recruiter_group)
        user.groups.add(self.hidden_auditor_group)

        forms = ApplicationForm.objects.get_forms_for_user(user)

        self.assertCountEqual(
            list(forms),
            [self.corp_app_form, self.hidden_corp_app_form],
        )

        for form in forms:
            if form == self.corp_app_form:
                self.assertFalse(form.is_auditor)
                self.assertTrue(form.is_recruiter)
                self.assertFalse(form.is_manager)
            elif form == self.hidden_corp_app_form:
                self.assertTrue(form.is_auditor)
                self.assertFalse(form.is_recruiter)
                self.assertFalse(form.is_manager)

    def test_get_auditor_forms_for_corp_auditor(self):
        user = AuthUtils.create_user("Auditor_Officer", disconnect_signals=True)
        user.groups.add(self.auditor_group)

        self.assertCountEqual(
            list(ApplicationForm.objects.get_auditor_forms_for_user(user)),
            [self.corp_app_form],
        )
        self.assertEqual(
            list(ApplicationForm.objects.get_recruiter_forms_for_user(user)),
            [],
        )
        self.assertEqual(
            list(ApplicationForm.objects.get_manager_forms_for_user(user)),
            [],
        )

    def test_get_recruiter_forms_for_corp_recruiter(self):
        user = AuthUtils.create_user("Recruiter_Officer", disconnect_signals=True)
        user.groups.add(self.recruiter_group)

        self.assertEqual(
            list(ApplicationForm.objects.get_auditor_forms_for_user(user)),
            [],
        )
        self.assertCountEqual(
            list(ApplicationForm.objects.get_recruiter_forms_for_user(user)),
            [self.corp_app_form],
        )
        self.assertEqual(
            list(ApplicationForm.objects.get_manager_forms_for_user(user)),
            [],
        )

    def test_get_manager_forms_for_corp_manager(self):
        user = AuthUtils.create_user("Manager_Officer", disconnect_signals=True)
        user.groups.add(self.manager_group)

        self.assertEqual(
            list(ApplicationForm.objects.get_auditor_forms_for_user(user)),
            [],
        )
        self.assertEqual(
            list(ApplicationForm.objects.get_recruiter_forms_for_user(user)),
            [],
        )
        self.assertCountEqual(
            list(ApplicationForm.objects.get_manager_forms_for_user(user)),
            [self.corp_app_form],
        )
