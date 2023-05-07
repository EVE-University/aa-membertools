# Standard Library
from datetime import timedelta
from unittest.mock import MagicMock, patch

# Third Party
from app_utils.esi_testing import EsiClientStub, EsiEndpoint
from app_utils.testing import NoSocketsTestCase
from bravado.exception import HTTPUnauthorized

# Django
from django.test import override_settings
from django.utils.dateparse import parse_datetime

# Alliance Auth
from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
from allianceauth.tests.auth_utils import AuthUtils
from esi.models import Token

from .. import tasks
from ..models import Application, ApplicationForm, ApplicationQuestion, Character

# TestTaskMail is a bit flawed right now as it doesn't verify the ESI call was called
# with the correct parameters, and it doesn't return a useful output to infer otherwise.
# TODO: Find a way to better test the ESI call parameters.


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
class TestTaskMail(NoSocketsTestCase):
    @patch("esi.models.Token.objects.get")
    def test_open_newmail_window(self, token_mock):
        token = MagicMock(
            spec=Token,
            id=1,
            character_id=1,
            character_name="Character 1",
            token_type="character",
            character_owner_hash="1",
        )

        token.get_esi_client.return_value = EsiClientStub(
            testdata={"User_Interface": {"post_ui_openwindow_newmail": None}},
            endpoints=[
                EsiEndpoint(
                    "User_Interface",
                    "post_ui_openwindow_newmail",
                )
            ],
        )

        token_mock.return_value = token

        ret = tasks.open_newmail_window([1], "Test Sub", "Test Body", token.id)

        token_mock.assert_called_with(id=token.id)
        self.assertTrue(ret)

    @patch("esi.models.Token.objects.get")
    def test_open_newmail_window_fails(self, token_mock):
        token = MagicMock(
            spec=Token,
            id=1,
            character_id=1,
            character_name="Character 1",
            token_type="character",
            character_owner_hash="1",
        )

        token.get_esi_client.return_value = EsiClientStub(
            testdata={"User_Interface": {"post_ui_openwindow_newmail": None}},
            endpoints=[
                EsiEndpoint(
                    "User_Interface",
                    "post_ui_openwindow_newmail",
                    http_error_code=401,
                )
            ],
        )

        token_mock.return_value = token

        with self.assertRaises(HTTPUnauthorized):
            tasks.open_newmail_window([1], "Test Sub", "Test Body", token.id)

        token_mock.assert_called_with(id=token.id)


@patch("membertools.tasks.close_expired_apps")
@patch("membertools.tasks.update_all_characters")
class TestMembertoolsPeriodic(NoSocketsTestCase):
    def test_membertools_periodic_has_expected_calls(self, update_mock, close_mock):
        tasks.membertools_periodic()

        update_mock.assert_called_with(False)
        close_mock.assert_called_with()

    def test_membertools_periodic_has_expected_calls_forced(
        self, update_mock, close_mock
    ):
        tasks.membertools_periodic(True)

        update_mock.assert_called_with(True)
        close_mock.assert_called_with()


class TestCloseExpiredApps(NoSocketsTestCase):
    @classmethod
    def setUpTestData(cls):
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

        cls.applicant_char = Character.objects.create(
            eve_character=cls.applicant_eve_char,
            member=None,
        )

        cls.applicant.profile.main_character = cls.applicant_eve_char
        cls.applicant.profile.save()

        CharacterOwnership.objects.create(
            user=cls.applicant,
            character=cls.applicant_eve_char,
            owner_hash="1",
        )

        cls.applications = [
            Application.objects.create(
                form=cls.corp_app_form,
                character=cls.applicant_char,
                eve_character=cls.applicant_eve_char,
                reviewer=cls.officer_eve_char,
                decision_by=cls.officer_eve_char,
                status=Application.STATUS_PROCESSED,
                decision=Application.DECISION_REJECT,
                submitted_on=parse_datetime("2020-01-01 00:01Z"),
                status_on=parse_datetime("2020-01-01 00:01Z"),
                decision_on=parse_datetime("2020-01-01 00:01Z"),
            ),
            Application.objects.create(
                form=cls.corp_app_form,
                character=cls.applicant_char,
                eve_character=cls.applicant_eve_char,
                reviewer=cls.officer_eve_char,
                decision_by=cls.officer_eve_char,
                status=Application.STATUS_PROCESSED,
                decision=Application.DECISION_REJECT,
                submitted_on=parse_datetime("2020-01-02 00:01Z"),
                status_on=parse_datetime("2020-01-02 00:01Z"),
                decision_on=parse_datetime("2020-01-02 00:01Z"),
            ),
            Application.objects.create(
                form=cls.corp_app_form,
                character=cls.applicant_char,
                eve_character=cls.applicant_eve_char,
                reviewer=cls.officer_eve_char,
                decision_by=cls.officer_eve_char,
                status=Application.STATUS_PROCESSED,
                decision=Application.DECISION_REJECT,
                submitted_on=parse_datetime("2020-01-02 00:01Z"),
                status_on=parse_datetime("2020-01-02 00:01Z"),
                decision_on=parse_datetime("2020-01-02 00:01Z"),
            ),
            Application.objects.create(
                form=cls.corp_app_form,
                character=cls.applicant_char,
                eve_character=cls.applicant_eve_char,
                reviewer=cls.officer_eve_char,
                decision_by=cls.officer_eve_char,
                status=Application.STATUS_PROCESSED,
                decision=Application.DECISION_REJECT,
                submitted_on=parse_datetime("2020-01-03 00:01Z"),
                status_on=parse_datetime("2020-01-03 00:01Z"),
                decision_on=parse_datetime("2020-01-03 00:01Z"),
            ),
            Application.objects.create(
                form=cls.corp_app_form,
                character=cls.applicant_char,
                eve_character=cls.applicant_eve_char,
                reviewer=cls.officer_eve_char,
                decision_by=cls.officer_eve_char,
                status=Application.STATUS_PROCESSED,
                decision=Application.DECISION_REJECT,
                submitted_on=parse_datetime("2020-01-04 00:01Z"),
                status_on=parse_datetime("2020-01-04 00:01Z"),
                decision_on=parse_datetime("2020-01-04 00:01Z"),
            ),
            Application.objects.create(
                form=cls.corp_app_form,
                character=cls.applicant_char,
                eve_character=cls.applicant_eve_char,
                reviewer=cls.officer_eve_char,
                decision_by=cls.officer_eve_char,
                status=Application.STATUS_PROCESSED,
                decision=Application.DECISION_REJECT,
                submitted_on=parse_datetime("2020-01-05 00:01Z"),
                status_on=parse_datetime("2020-01-05 00:01Z"),
                decision_on=parse_datetime("2020-01-05 00:01Z"),
            ),
        ]
        AuthUtils.connect_signals()

        return super().setUpTestData()

    @patch("membertools.tasks.MEMBERTOOLS_APP_ARCHIVE_TIME", timedelta(days=14))
    def test_no_apps_expired(self):
        test_datetime = parse_datetime("2020-01-01 00:01Z")

        with patch("django.utils.timezone.now", return_value=test_datetime) as now_mock:
            ret = tasks.close_expired_apps()

        self.assertEqual(ret, 0)
        now_mock.assert_called()

        apps = Application.objects.all()
        self.assertEqual(apps[0].status, Application.STATUS_PROCESSED)
        self.assertEqual(apps[0].closed_on, None)

        self.assertEqual(apps[1].status, Application.STATUS_PROCESSED)
        self.assertEqual(apps[1].closed_on, None)

        self.assertEqual(apps[2].status, Application.STATUS_PROCESSED)
        self.assertEqual(apps[2].closed_on, None)

        self.assertEqual(apps[3].status, Application.STATUS_PROCESSED)
        self.assertEqual(apps[3].closed_on, None)

        self.assertEqual(apps[4].status, Application.STATUS_PROCESSED)
        self.assertEqual(apps[4].closed_on, None)

        self.assertEqual(apps[5].status, Application.STATUS_PROCESSED)
        self.assertEqual(apps[5].closed_on, None)

    @patch("membertools.tasks.MEMBERTOOLS_APP_ARCHIVE_TIME", timedelta(days=1))
    def test_one_app_expired(self):
        test_datetime = parse_datetime("2020-01-02 00:01Z")

        with patch("django.utils.timezone.now", return_value=test_datetime) as now_mock:
            ret = tasks.close_expired_apps()

        self.assertEqual(ret, 1)
        now_mock.assert_called()

        apps = Application.objects.all()

        self.assertEqual(apps[0].status, Application.STATUS_CLOSED)
        self.assertEqual(apps[0].closed_on, test_datetime)

        self.assertEqual(apps[1].status, Application.STATUS_PROCESSED)
        self.assertEqual(apps[1].closed_on, None)

        self.assertEqual(apps[2].status, Application.STATUS_PROCESSED)
        self.assertEqual(apps[2].closed_on, None)

        self.assertEqual(apps[3].status, Application.STATUS_PROCESSED)
        self.assertEqual(apps[3].closed_on, None)

        self.assertEqual(apps[4].status, Application.STATUS_PROCESSED)
        self.assertEqual(apps[4].closed_on, None)

        self.assertEqual(apps[5].status, Application.STATUS_PROCESSED)
        self.assertEqual(apps[5].closed_on, None)

    @patch("membertools.tasks.MEMBERTOOLS_APP_ARCHIVE_TIME", timedelta(days=1))
    def test_all_apps_expired(self):
        test_datetime = parse_datetime("2020-01-10 00:01Z")

        with patch("django.utils.timezone.now", return_value=test_datetime) as now_mock:
            ret = tasks.close_expired_apps()

        self.assertEqual(ret, 6)
        now_mock.assert_called()

        apps = Application.objects.all()

        self.assertEqual(apps[0].status, Application.STATUS_CLOSED)
        self.assertEqual(apps[0].closed_on, test_datetime)

        self.assertEqual(apps[1].status, Application.STATUS_CLOSED)
        self.assertEqual(apps[1].closed_on, test_datetime)

        self.assertEqual(apps[2].status, Application.STATUS_CLOSED)
        self.assertEqual(apps[2].closed_on, test_datetime)

        self.assertEqual(apps[3].status, Application.STATUS_CLOSED)
        self.assertEqual(apps[3].closed_on, test_datetime)

        self.assertEqual(apps[4].status, Application.STATUS_CLOSED)
        self.assertEqual(apps[4].closed_on, test_datetime)

        self.assertEqual(apps[5].status, Application.STATUS_CLOSED)
        self.assertEqual(apps[5].closed_on, test_datetime)
