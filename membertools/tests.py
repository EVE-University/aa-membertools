from django.contrib.auth.models import User
from django.test import TestCase

from allianceauth.eveonline.models import EveCorporationInfo
from allianceauth.tests.auth_utils import AuthUtils

from .models import Application, ApplicationForm, ApplicationQuestion, ApplicationChoice


class TestApplicationManagersPendingRequestsCountForUser(TestCase):
    def setUp(self) -> None:
        self.corporation_1 = EveCorporationInfo.objects.create(
            corporation_id=2001, corporation_name="Wayne Tech", member_count=42
        )
        self.corporation_2 = EveCorporationInfo.objects.create(
            corporation_id=2011, corporation_name="Lex Corp", member_count=666
        )
        question = ApplicationQuestion.objects.create(title="Dummy Question")
        ApplicationChoice.objects.create(question=question, choice_text="yes")
        ApplicationChoice.objects.create(question=question, choice_text="no")
        self.form_corporation_1 = ApplicationForm.objects.create(
            corp=self.corporation_1
        )
        self.form_corporation_1.questions.add(question)
        self.form_corporation_2 = ApplicationForm.objects.create(
            corp=self.corporation_2
        )
        self.form_corporation_2.questions.add(question)

        self.user_requestor = AuthUtils.create_member("Peter Parker")

        self.user_manager = AuthUtils.create_member("Bruce Wayne")
        AuthUtils.add_main_character_2(
            self.user_manager,
            self.user_manager.username,
            1001,
            self.corporation_1.corporation_id,
            self.corporation_1.corporation_name,
        )
        AuthUtils.add_permission_to_user_by_name(
            "auth.human_resources", self.user_manager
        )
        self.user_manager = User.objects.get(pk=self.user_manager.pk)

    def test_no_pending_application(self):
        # given manager of corporation 1 has permission
        # when no application is pending for corporation 1
        # return 0
        self.assertEqual(
            Application.objects.pending_requests_count_for_user(self.user_manager), 0
        )

    def test_single_pending_application(self):
        # given manager of corporation 1 has permission
        # when 1 application is pending for corporation 1
        # return 1
        Application.objects.create(
            form=self.form_corporation_1, user=self.user_requestor
        )
        self.assertEqual(
            Application.objects.pending_requests_count_for_user(self.user_manager), 1
        )

    def test_user_has_no_permission(self):
        # given user has no permission
        # when 1 application is pending
        # return None
        self.assertIsNone(
            Application.objects.pending_requests_count_for_user(self.user_requestor)
        )

    def test_two_pending_applications_for_different_corporations_normal_manager(self):
        # given manager of corporation 1 has permission
        # when 1 application is pending for corporation 1
        # and 1 application is pending for corporation 2
        # return 1
        Application.objects.create(
            form=self.form_corporation_1, user=self.user_requestor
        )
        Application.objects.create(
            form=self.form_corporation_2, user=self.user_requestor
        )
        self.assertEqual(
            Application.objects.pending_requests_count_for_user(self.user_manager), 1
        )

    def test_two_pending_applications_for_different_corporations_manager_is_super(self):
        # given manager of corporation 1 has permission
        # when 1 application is pending for corporation 1
        # and 1 application is pending for corporation 2
        # return 1
        Application.objects.create(
            form=self.form_corporation_1, user=self.user_requestor
        )
        Application.objects.create(
            form=self.form_corporation_2, user=self.user_requestor
        )
        superuser = User.objects.create_superuser(
            "Superman", "superman@example.com", "password"
        )
        self.assertEqual(
            Application.objects.pending_requests_count_for_user(superuser), 2
        )
