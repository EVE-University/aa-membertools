# Django
from django.test import TestCase

from ..models import ApplicationTitle, _get_app_title_all


class TestModelApplication(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.titles = []
        for i in range(4):
            title = ApplicationTitle.objects.create(name=f"Title {i}", priority=i + 1)
            setattr(cls, f"title_{i}", title)
            cls.titles.append(title)
        return super().setUpTestData()

    def test__get_app_title_all(self):
        titles = _get_app_title_all()

        self.assertCountEqual(self.titles, titles)

    def test_app_title_str(self):
        self.assertEqual(str(self.title_1), "Title 1")

    def test_app_title_compare_ge(self):
        self.assertTrue(self.title_3 >= self.title_2)
        self.assertTrue(self.title_2 >= self.title_2)
        self.assertFalse(self.title_1 >= self.title_2)

    def test_app_title_compare_le(self):
        self.assertTrue(self.title_2 <= self.title_3)
        self.assertTrue(self.title_2 <= self.title_2)
        self.assertFalse(self.title_2 <= self.title_1)

    def test_app_title_compare_gt(self):
        self.assertTrue(self.title_3 > self.title_2)
        self.assertFalse(self.title_1 > self.title_2)

    def test_app_title_compare_lt(self):
        self.assertTrue(self.title_2 < self.title_3)
        self.assertFalse(self.title_2 < self.title_1)
