# Django
from django.urls import path

from . import views

app_name = "membertools_admin"

urlpatterns = [
    path("", views.hr_admin_dashboard_view, name="index"),
    path("queue", views.hr_admin_queue_view, name="queue"),
    path("archive", views.hr_admin_archive_view, name="archive"),
    path(
        "archive/<str:app_status>", views.hr_admin_archive_view, name="archive_status"
    ),
    path("remove/<int:app_id>", views.hr_admin_remove, name="remove"),
    path("view/<int:app_id>", views.hr_admin_view, name="view"),
    path(
        "view/<int:app_id>/comment/new",
        views.hr_admin_comment_create,
        name="comment_create",
    ),
    path(
        "view/<int:app_id>/update_memberaudit",
        views.hr_admin_app_update_memberaudit,
        name="memberaudit_update",
    ),
    path(
        "view/<int:app_id>/comment/<int:comment_id>/edit",
        views.hr_admin_comment_edit,
        name="comment_edit",
    ),
    path(
        "view/<int:app_id>/comment/<int:comment_id>/delete",
        views.hr_admin_comment_delete,
        name="comment_delete",
    ),
    path(
        "action/approve/<int:app_id>",
        views.hr_admin_approve_action,
        name="action_approve",
    ),
    path(
        "action/release/<int:app_id>",
        views.hr_admin_release_action,
        name="action_release",
    ),
    path(
        "action/wait/<int:app_id>",
        views.hr_admin_wait_action,
        name="action_wait",
    ),
    path(
        "action/reject/<int:app_id>", views.hr_admin_reject_action, name="action_reject"
    ),
    path(
        "action/withdraw/<int:app_id>",
        views.hr_admin_withdraw_action,
        name="action_withdraw",
    ),
    path("action/close/<int:app_id>", views.hr_admin_close_action, name="action_close"),
    path(
        "action/start_review/<int:app_id>",
        views.hr_admin_start_review_action,
        name="action_start_review",
    ),
    path("char/", views.hr_admin_char_detail_index, name="char_detail_index"),
    path(
        "char/eve_id/<int:char_id>",
        views.hr_admin_char_detail_lookup,
        name="char_detail_lookup",
    ),
    path(
        "char/<int:char_id>/update_memberaudit",
        views.hr_admin_char_update_memberaudit,
        name="char_detail_memberaudit_update",
    ),
    path(
        "char/<int:char_detail_id>",
        views.hr_admin_char_detail_view,
        name="char_detail_view",
    ),
    path(
        "char/<int:char_id>/comment/new",
        views.hr_admin_char_detail_comment_create,
        name="char_detail_comment_create",
    ),
    path(
        "char/<int:char_id>/comment/<int:comment_id>/edit",
        views.hr_admin_char_detail_comment_edit,
        name="char_detail_comment_edit",
    ),
    path(
        "char/<int:char_id>/comment/<int:comment_id>/delete",
        views.hr_admin_char_detail_comment_delete,
        name="char_detail_comment_delete",
    ),
]
