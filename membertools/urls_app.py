# Django
from django.urls import path

from . import views

app_name = "membertools"

urlpatterns = [
    path(
        "",
        views.hr_app_dashboard_view,
        name="index",
    ),
    path(
        "create/<int:form_id>",
        views.hr_app_create_view,
        name="create",
    ),
    path(
        "view/<int:app_id>",
        views.hr_app_view,
        name="view",
    ),
    path(
        "archive/",
        views.hr_app_archive_view,
        name="archive",
    ),
    path(
        "remove/<int:app_id>",
        views.hr_app_remove,
        name="remove",
    ),
]
