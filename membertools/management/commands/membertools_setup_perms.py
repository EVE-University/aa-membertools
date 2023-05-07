# Django
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

# EVE Uni Member Tools
from membertools.models import (
    Application,
    ApplicationAction,
    ApplicationChoice,
    ApplicationForm,
    ApplicationQuestion,
    ApplicationResponse,
    ApplicationTitle,
    Character,
    CharacterCorpHistory,
    CharacterLink,
    CharacterUpdateStatus,
    Comment,
    General,
    Member,
    TitleFilter,
)


class Command(BaseCommand):
    help = "Performs Permission setup for E-Uni and removes old hrappsnext permissions."

    def handle(self, *args, **options):
        # Groups
        director = Group.objects.get(name="Director")
        web_mgr = Group.objects.get(name="Manager (Web Services)")
        intake_mgr = Group.objects.get(name="Manager (Intake & Progression)")
        intake_snr = Group.objects.get(name="Senior Intake & Progression Officer")
        intake_ofc = Group.objects.get(name="Intake & Progression Officer")
        orient_mgr = Group.objects.get(name="Manager (Orientation)")
        orient_snr = Group.objects.get(name="Senior Orientation Officer")
        orient_ofc = Group.objects.get(name="Orientation Officer")

        # General
        general_type = ContentType.objects.get_for_model(General)
        general_basic = Permission.objects.get(
            content_type=general_type, codename="basic_access"
        )
        general_admin = Permission.objects.get(
            content_type=general_type, codename="admin_access"
        )
        general_char = Permission.objects.get(
            content_type=general_type, codename="character_admin_access"
        )
        general_app = Permission.objects.get(
            content_type=general_type, codename="application_admin_access"
        )
        general_queue = Permission.objects.get(
            content_type=general_type, codename="queue_admin_access"
        )

        # ApplicationQuestion
        app_question_type = ContentType.objects.get_for_model(ApplicationQuestion)
        app_question_add = Permission.objects.get(
            content_type=app_question_type, codename="add_applicationquestion"
        )
        app_question_change = Permission.objects.get(
            content_type=app_question_type, codename="change_applicationquestion"
        )
        app_question_delete = Permission.objects.get(
            content_type=app_question_type, codename="delete_applicationquestion"
        )
        app_question_view = Permission.objects.get(
            content_type=app_question_type, codename="view_applicationquestion"
        )

        # ApplicationChoice
        app_choice_type = ContentType.objects.get_for_model(ApplicationChoice)
        app_choice_add = Permission.objects.get(
            content_type=app_choice_type, codename="add_applicationchoice"
        )
        app_choice_change = Permission.objects.get(
            content_type=app_choice_type, codename="change_applicationchoice"
        )
        app_choice_delete = Permission.objects.get(
            content_type=app_choice_type, codename="delete_applicationchoice"
        )
        app_choice_view = Permission.objects.get(
            content_type=app_choice_type, codename="view_applicationchoice"
        )

        # ApplicationTitle
        app_title_type = ContentType.objects.get_for_model(ApplicationTitle)
        app_title_add = Permission.objects.get(
            content_type=app_title_type, codename="add_applicationtitle"
        )
        app_title_change = Permission.objects.get(
            content_type=app_title_type, codename="change_applicationtitle"
        )
        app_title_delete = Permission.objects.get(
            content_type=app_title_type, codename="delete_applicationtitle"
        )
        app_title_view = Permission.objects.get(
            content_type=app_title_type, codename="view_applicationtitle"
        )

        # ApplicationForm
        app_form_type = ContentType.objects.get_for_model(ApplicationForm)
        app_form_add = Permission.objects.get(
            content_type=app_form_type, codename="add_applicationform"
        )
        app_form_change = Permission.objects.get(
            content_type=app_form_type, codename="change_applicationform"
        )
        app_form_delete = Permission.objects.get(
            content_type=app_form_type, codename="delete_applicationform"
        )
        app_form_view = Permission.objects.get(
            content_type=app_form_type, codename="view_applicationform"
        )

        # Application
        app_type = ContentType.objects.get_for_model(Application)
        app_add = Permission.objects.get(
            content_type=app_type, codename="add_application"
        )
        app_change = Permission.objects.get(
            content_type=app_type, codename="change_application"
        )
        app_delete = Permission.objects.get(
            content_type=app_type, codename="delete_application"
        )
        app_view = Permission.objects.get(
            content_type=app_type, codename="view_application"
        )
        app_review = Permission.objects.get(
            content_type=app_type, codename="review_application"
        )
        app_reject = Permission.objects.get(
            content_type=app_type, codename="reject_application"
        )
        app_manage = Permission.objects.get(
            content_type=app_type, codename="manage_application"
        )

        # ApplicationResponse
        app_response_type = ContentType.objects.get_for_model(ApplicationResponse)
        app_response_add = Permission.objects.get(
            content_type=app_response_type, codename="add_applicationresponse"
        )
        app_response_change = Permission.objects.get(
            content_type=app_response_type, codename="change_applicationresponse"
        )
        app_response_delete = Permission.objects.get(
            content_type=app_response_type, codename="delete_applicationresponse"
        )
        app_response_view = Permission.objects.get(
            content_type=app_response_type, codename="view_applicationresponse"
        )

        # ApplicationAction
        app_action_type = ContentType.objects.get_for_model(ApplicationAction)
        app_action_add = Permission.objects.get(
            content_type=app_action_type, codename="add_applicationaction"
        )
        app_action_change = Permission.objects.get(
            content_type=app_action_type, codename="change_applicationaction"
        )
        app_action_delete = Permission.objects.get(
            content_type=app_action_type, codename="delete_applicationaction"
        )
        app_action_view = Permission.objects.get(
            content_type=app_action_type, codename="view_applicationaction"
        )

        # Comment
        comment_type = ContentType.objects.get_for_model(Comment)
        comment_add = Permission.objects.get(
            content_type=comment_type, codename="add_comment"
        )
        comment_change = Permission.objects.get(
            content_type=comment_type, codename="change_comment"
        )
        comment_delete = Permission.objects.get(
            content_type=comment_type, codename="delete_comment"
        )
        comment_view = Permission.objects.get(
            content_type=comment_type, codename="view_comment"
        )

        # Member
        member_type = ContentType.objects.get_for_model(Member)
        member_add = Permission.objects.get(
            content_type=member_type, codename="add_member"
        )
        member_change = Permission.objects.get(
            content_type=member_type, codename="change_member"
        )
        member_delete = Permission.objects.get(
            content_type=member_type, codename="delete_member"
        )
        member_view = Permission.objects.get(
            content_type=member_type, codename="view_member"
        )

        # Character
        character_type = ContentType.objects.get_for_model(Character)
        character_add = Permission.objects.get(
            content_type=character_type, codename="add_character"
        )
        character_change = Permission.objects.get(
            content_type=character_type, codename="change_character"
        )
        character_delete = Permission.objects.get(
            content_type=character_type, codename="delete_character"
        )
        character_view = Permission.objects.get(
            content_type=character_type, codename="view_character"
        )

        # CharacterCorpHistory
        char_corp_history_type = ContentType.objects.get_for_model(CharacterCorpHistory)
        char_corp_history_add = Permission.objects.get(
            content_type=char_corp_history_type, codename="add_charactercorphistory"
        )
        char_corp_history_change = Permission.objects.get(
            content_type=char_corp_history_type, codename="change_charactercorphistory"
        )
        char_corp_history_delete = Permission.objects.get(
            content_type=char_corp_history_type, codename="delete_charactercorphistory"
        )
        char_corp_history_view = Permission.objects.get(
            content_type=char_corp_history_type, codename="view_charactercorphistory"
        )

        # CharacterUpdateStatus
        char_update_status_type = ContentType.objects.get_for_model(
            CharacterUpdateStatus
        )
        char_update_status_add = Permission.objects.get(
            content_type=char_update_status_type, codename="add_characterupdatestatus"
        )
        char_update_status_change = Permission.objects.get(
            content_type=char_update_status_type,
            codename="change_characterupdatestatus",
        )
        char_update_status_delete = Permission.objects.get(
            content_type=char_update_status_type,
            codename="delete_characterupdatestatus",
        )
        char_update_status_view = Permission.objects.get(
            content_type=char_update_status_type, codename="view_characterupdatestatus"
        )

        # CharacterLink
        char_link_type = ContentType.objects.get_for_model(CharacterLink)
        char_link_add = Permission.objects.get(
            content_type=char_link_type, codename="add_characterlink"
        )
        char_link_change = Permission.objects.get(
            content_type=char_link_type, codename="change_characterlink"
        )
        char_link_delete = Permission.objects.get(
            content_type=char_link_type, codename="delete_characterlink"
        )
        char_link_view = Permission.objects.get(
            content_type=char_link_type, codename="view_characterlink"
        )

        # TitleFilter
        title_filter_type = ContentType.objects.get_for_model(TitleFilter)
        title_filter_add = Permission.objects.get(
            content_type=title_filter_type, codename="add_titlefilter"
        )
        title_filter_change = Permission.objects.get(
            content_type=title_filter_type, codename="change_titlefilter"
        )
        title_filter_delete = Permission.objects.get(
            content_type=title_filter_type, codename="delete_titlefilter"
        )
        title_filter_view = Permission.objects.get(
            content_type=title_filter_type, codename="view_titlefilter"
        )

        with transaction.atomic():
            # Director
            director.permissions.add(
                # General
                general_basic,
                general_admin,
                general_char,
                general_app,
                general_queue,
                # ApplicationQuestion
                app_question_add,
                app_question_change,
                app_question_delete,
                app_question_view,
                # ApplicationChoice
                app_choice_add,
                app_choice_change,
                app_choice_delete,
                app_choice_view,
                # ApplicationTitle
                app_title_add,
                app_title_change,
                app_title_delete,
                app_title_view,
                # ApplicationForm
                app_form_add,
                app_form_change,
                app_form_delete,
                app_form_view,
                # Application
                app_add,
                app_change,
                app_delete,
                app_view,
                app_review,
                app_reject,
                app_manage,
                # ApplicationResponse
                app_response_add,
                app_response_change,
                app_response_delete,
                app_response_view,
                # ApplicationAction
                app_action_add,
                app_action_change,
                app_action_delete,
                app_action_view,
                # Comment
                comment_add,
                comment_change,
                comment_delete,
                comment_view,
                # Member
                member_add,
                member_change,
                member_delete,
                member_view,
                # Character
                character_add,
                character_change,
                character_delete,
                character_view,
                # CharacterCorpHistory
                char_corp_history_add,
                char_corp_history_change,
                char_corp_history_delete,
                char_corp_history_view,
                # CharacterUpdateStatus
                char_update_status_add,
                char_update_status_change,
                char_update_status_delete,
                char_update_status_view,
                # CharacterLink
                char_link_add,
                char_link_change,
                char_link_delete,
                char_link_view,
                # TitleFilter
                title_filter_add,
                title_filter_change,
                title_filter_delete,
                title_filter_view,
            )

            # Web Services Manager
            web_mgr.permissions.add(
                # General
                general_basic,
                general_admin,
                general_char,
                general_app,
                general_queue,
                # ApplicationQuestion
                app_question_add,
                app_question_change,
                app_question_delete,
                app_question_view,
                # ApplicationChoice
                app_choice_add,
                app_choice_change,
                app_choice_delete,
                app_choice_view,
                # ApplicationTitle
                app_title_add,
                app_title_change,
                app_title_delete,
                app_title_view,
                # ApplicationForm
                app_form_add,
                app_form_change,
                app_form_delete,
                app_form_view,
                # Application
                app_add,
                app_change,
                app_delete,
                app_view,
                app_review,
                app_reject,
                app_manage,
                # ApplicationResponse
                app_response_add,
                app_response_change,
                app_response_delete,
                app_response_view,
                # ApplicationAction
                app_action_add,
                app_action_change,
                app_action_delete,
                app_action_view,
                # Comment
                comment_add,
                comment_change,
                comment_delete,
                comment_view,
                # Member
                member_add,
                member_change,
                member_delete,
                member_view,
                # Character
                character_add,
                character_change,
                character_delete,
                character_view,
                # CharacterCorpHistory
                char_corp_history_add,
                char_corp_history_change,
                char_corp_history_delete,
                char_corp_history_view,
                # CharacterUpdateStatus
                char_update_status_add,
                char_update_status_change,
                char_update_status_delete,
                char_update_status_view,
                # CharacterLink
                char_link_add,
                char_link_change,
                char_link_delete,
                char_link_view,
                # TitleFilter
                title_filter_add,
                title_filter_change,
                title_filter_delete,
                title_filter_view,
            )

            # Intake Manager
            intake_mgr.permissions.add(
                # General
                general_basic,
                general_admin,
                general_char,
                general_app,
                general_queue,
                # ApplicationQuestion
                app_question_add,
                app_question_change,
                app_question_delete,
                app_question_view,
                # ApplicationChoice
                app_choice_add,
                app_choice_change,
                app_choice_delete,
                app_choice_view,
                # ApplicationTitle
                app_title_add,
                app_title_change,
                app_title_delete,
                app_title_view,
                # ApplicationForm
                app_form_add,
                app_form_change,
                app_form_delete,
                app_form_view,
                # Application
                app_add,
                app_change,
                app_delete,
                app_view,
                app_review,
                app_reject,
                app_manage,
                # ApplicationResponse
                app_response_add,
                app_response_change,
                app_response_delete,
                app_response_view,
                # ApplicationAction
                app_action_view,
                # Comment
                comment_add,
                comment_change,
                comment_delete,
                comment_view,
                # Member
                member_change,
                member_view,
                # Character
                character_change,
                character_view,
                # CharacterUpdateStatus
                char_update_status_view,
            )

            # Senior Intake Officer
            intake_snr.permissions.add(
                # General
                general_basic,
                general_admin,
                general_char,
                general_app,
                general_queue,
                # Application
                app_view,
                app_review,
                app_reject,
                app_manage,
                # Comment
                comment_add,
                comment_change,
                comment_delete,
                comment_view,
                # Member
                member_view,
                # Character
                character_view,
            )

            # Intake Officer
            intake_ofc.permissions.add(
                # General
                general_basic,
                general_admin,
                general_char,
                general_app,
                general_queue,
                # Application
                app_view,
                app_review,
                app_reject,
                # Comment
                comment_add,
                comment_view,
                # Member
                member_view,
                # Character
                character_view,
            )

            # Orientation Manager
            orient_mgr.permissions.add(
                # General
                general_basic,
                general_admin,
                general_char,
                general_app,
                general_queue,
                # Application
                app_view,
                # Comment
                comment_view,
                # Member
                member_view,
                # Character
                character_view,
            )

            # Senior Orientation Officer
            orient_snr.permissions.add(
                # General
                general_basic,
                general_admin,
                general_char,
                general_app,
                # Application
                app_view,
                # Comment
                comment_view,
                # Member
                member_view,
                # Character
                character_view,
            )

            # Orientation Officer
            orient_ofc.permissions.add(
                # General
                general_basic,
                general_admin,
                general_char,
                general_app,
                # Application
                app_view,
                # Comment
                comment_view,
                # Member
                member_view,
                # Character
                character_view,
            )

            # Remove old hrappsnext permissions
            Permission.objects.filter(
                content_type__in=ContentType.objects.filter(app_label="hrappsnext")
            ).delete()
