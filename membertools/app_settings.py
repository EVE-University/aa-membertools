# Standard Library
from datetime import timedelta

# Third Party
from app_utils.django import clean_setting

# Django
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

MEMBERTOOLS_MAIN_CORP_ID = clean_setting(
    "MEMBERTOOLS_MAIN_CORP_ID", 917701062, required_type=int
)

MEMBERTOOLS_APP_NAME = clean_setting("MEMBERTOOLS_APP_NAME", _("Member Admin"))
MEMBERTOOLS_ADMIN_NAME = clean_setting("MEMBERTOOLS_ADMIN_NAME", MEMBERTOOLS_APP_NAME)

MEMBERTOOLS_APP_MENU_TITLE = clean_setting(
    "MEMBERTOOLS_APP_MENU_TITLE", _("Applications")
)
MEMBERTOOLS_ADMIN_MENU_TITLE = clean_setting(
    "MEMBERTOOLS_ADMIN_MENU_TITLE", _("Member Admin")
)

MEMBERTOOLS_APP_BASE_URL = clean_setting(
    "MEMBERTOOLS_BASE_URL", slugify("app", allow_unicode=True), required_type=str
)
MEMBERTOOLS_ADMIN_BASE_URL = clean_setting(
    "MEMBERTOOLS_ADMIN_BASE_URL", slugify("mad", allow_unicode=True), required_type=str
)

# Duration settings
MEMBERTOOLS_APP_ARCHIVE_TIME = clean_setting(
    "MEMBERTOOLS_APP_ARCHIVE_TIME", timedelta(days=14), required_type=timedelta
)

MEMBERTOOLS_COMMENT_SELF_EDIT_TIME = clean_setting(
    "MEMBERTOOLS_COMMENT_SELF_EDIT_TIME", timedelta(days=1), required_type=timedelta
)
MEMBERTOOLS_COMMENT_SELF_DELETE_TIME = clean_setting(
    "MEMBERTOOLS_COMMENT_SELF_DELETE_TIME",
    timedelta(minutes=15),
    required_type=timedelta,
)

# Tasks
MEMBERTOOLS_TASKS_FOREGROUND_PRIORITY = clean_setting(
    "MEMBERTOOLS_TASKS_FOREGROUND_PRIORITY",
    8,
    required_type=int,
    min_value=1,
    max_value=9,
)
MEMBERTOOLS_TASKS_BACKGROUND_PRIORITY = clean_setting(
    "MEMBERTOOLS_TASKS_BACKGROUND_PRIORITY",
    5,
    required_type=int,
    min_value=1,
    max_value=9,
)
