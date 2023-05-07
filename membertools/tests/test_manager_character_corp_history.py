# Standard Library
# from datetime import datetime
# from unittest.mock import patch

# Django
from django.test import TestCase

from ..models import Character

# from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
# from allianceauth.eveonline.providers import Corporation, ObjectNotFound


class TestManagerCharacterCorpHistory(TestCase):
    @classmethod
    def setUpTestData(cls):
        return super().setUpTestData()

    def test_update_char(self):
        # TODO: Implent this test case for when(if) CCP returns the corp history endpoint
        self.skipTest("ESI Corp History endpoint is disabled by CCP")

        Character.corporation_history[0]
