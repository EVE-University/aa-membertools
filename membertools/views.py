import humanize
import unicodedata

from datetime import timedelta
from email import message

from django.apps import apps
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.core.paginator import Paginator
from django.conf import settings
from django.contrib import messages
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseNotAllowed,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.decorators import user_passes_test
from django.forms import ValidationError
from django.shortcuts import render, get_object_or_404, redirect, Http404
from django.db import transaction, IntegrityError, ProgrammingError
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from esi.decorators import token_required, tokens_required
from esi.clients import EsiClientProvider

from allianceauth.notifications import notify
from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCharacter
from allianceauth.services.hooks import get_extension_logger

from .app_settings import (
    MEMBERTOOLS_APP_ARCHIVE_TIME,
    MEMBERTOOLS_APP_NAME,
    MEMBERTOOLS_ADMIN_NAME,
    MEMBERTOOLS_COMMENT_SELF_EDIT_TIME,
    MEMBERTOOLS_COMMENT_SELF_DELETE_TIME,
)

from .models import Application, ApplicationAction, Character, Member
from .models import Comment
from .models import ApplicationForm
from .models import ApplicationResponse


from .forms import CommentForm, SearchForm

from .checks import Check

from .helpers import open_newmail_window_from_template

from . import tasks

logger = get_extension_logger(__name__)
esi = EsiClientProvider()


def get_user_characters(request, character):
    if not character.character_ownership.user:
        characters = EveCharacter.objects.none()
    else:
        characters = EveCharacter.objects.select_related("next_character").filter(
            character_ownership__user=character.character_ownership.user
        )

    return characters


def is_form_recruiter(form, user, perm="membertools.approve_application") -> bool:
    """Returns true if user is superuser or belongs to a group in the recruiter_groups list for the form."""
    if user.is_superuser:
        return True
    return (
        user.has_perm(perm)
        & form.recruiter_groups.filter(
            authgroup__in=user.groups.values_list("pk").all()
        ).exists()
    )


def is_form_manager(form, user, perm="membertools.manage_application") -> bool:
    """Returns true if user is superuser or belongs to a group in the manager_groups list for the form."""
    if user.is_superuser:
        return True
    return (
        user.has_perm(perm)
        & form.manager_groups.filter(
            authgroup__in=user.groups.values_list("pk").all()
        ).exists()
    )


def get_checks(
    user: settings.AUTH_USER_MODEL, character: EveCharacter, request: HttpRequest
) -> dict:
    check = Check.get_instance(user, character, request)
    checks = {}
    checks["verified"] = check.check("verified", user, character)
    checks["memberaudit"] = check.check("memberaudit", user, character)
    checks["discord"] = check.check("discord", user, character)
    checks["mumble"] = check.check("mumble", user, character)
    checks["phpbb3"] = check.check("phpbb3", user, character)

    return checks


# Shared context funcs
def hr_app_add_shared_context(request, context: dict) -> dict:
    new_context = {
        "app_title": MEMBERTOOLS_APP_NAME,
    }

    new_context.update(context)

    return new_context


def hr_admin_add_shared_context(request, context: dict) -> dict:
    new_context = {
        "app_title": MEMBERTOOLS_ADMIN_NAME,
        "memberaudit": apps.is_installed("memberaudit"),
    }

    new_context.update(context)

    return new_context


# Applicant Views


@login_required
@permission_required("membertools.basic_access")
def hr_app_dashboard_view(request):
    cutoff_date = timezone.now() - MEMBERTOOLS_APP_ARCHIVE_TIME
    current_apps = (
        Application.objects.select_related(
            "eve_character__character_ownership__user",
            "form",
            "form__corp",
            "form__title",
        )
        .filter(eve_character__character_ownership__user=request.user)
        .filter(
            Q(decision=Application.DECISION_PENDING) | Q(decision_on__gte=cutoff_date)
        )
    )

    available_forms = []
    for form in ApplicationForm.objects.all():
        chars = form.get_user_eligible_chars(request.user)
        if not len(chars):
            continue
        available_forms.append(form)

    context = {
        "page_title": "My Applications",
        "current_apps": current_apps,
        "available_forms": available_forms,
    }

    return render(
        request,
        "membertools/dashboard.html",
        hr_app_add_shared_context(request, context),
    )


@login_required
@permission_required("membertools.basic_access")
def hr_app_archive_view(request):
    cutoff_date = timezone.now() - MEMBERTOOLS_APP_ARCHIVE_TIME
    applications = Application.objects.select_related(
        "eve_character__character_ownership__user", "form", "form__corp", "form__title"
    ).filter(
        eve_character__character_ownership__user=request.user,
        decision__in=[
            Application.DECISION_ACCEPT,
            Application.DECISION_REJECT,
            Application.DECISION_WITHDRAW,
        ],
        decision_on__lte=cutoff_date,
    )

    context = {
        "page_title": _("Past Applications"),
        "applications": applications,
        "application_delta_human": humanize.naturaldelta(MEMBERTOOLS_APP_ARCHIVE_TIME),
    }

    return render(
        request,
        "membertools/app_archive.html",
        hr_app_add_shared_context(request, context),
    )


@login_required
@permission_required("membertools.basic_access")
def hr_app_view(request, app_id):
    logger.debug("hr_app_view called by user %s for app id %s", request.user, app_id)
    try:
        app = Application.objects.prefetch_related("responses").get(pk=app_id)
    except Application.DoesNotExist:
        raise Http404

    if app.user != request.user:
        logger.warning(
            "User %s does not have permission to view apps for %s.",
            request.user,
            app.form,
        )
        raise Http404

    context = {
        "page_title": _("View Application") + f": {app.character}",
        "sub_title": str(app.form),
        "app": app,
        "checks": get_checks(app.user, app.eve_character, request),
        "responses": app.responses.all(),
    }
    return render(
        request,
        "membertools/app_view.html",
        hr_app_add_shared_context(request, context),
    )


@login_required
@permission_required("membertools.basic_access")
def hr_app_create_view(request, form_id):
    form = get_object_or_404(ApplicationForm, id=form_id)
    questions = form.questions.all()
    application = None
    characters = form.get_user_eligible_chars(request.user)

    if not len(characters):
        logger.error(
            "%s called hr_app_create_view for %s form without any eligible characters.",
            request.user,
            form,
        )
        return redirect("membertools:index")

    # Handle submission
    if request.method == "POST":
        try:
            # Use Member row if user has one available.
            try:
                member = request.user.profile.main_character.next_character.member
            except ObjectDoesNotExist:
                member = None

            selected_character_id = int(request.POST.get("selected_character_id", 0))
            if not selected_character_id:
                raise CharacterOwnership.DoesNotExist

            selected_character = CharacterOwnership.objects.get(
                user=request.user, character__character_id=selected_character_id
            ).character

            detail, __ = Character.objects.update_or_create(
                eve_character=selected_character,
                defaults={"eve_character": selected_character, "member": member},
            )

            tasks.update_character.delay(detail.id, True)

            # Check if we have valid question answers
            valid = True

            for question in questions:
                if question.multi_select:
                    answer = request.POST.getlist(str(question.pk), "")
                else:
                    answer = request.POST.get(str(question.pk), "").strip()
                question.answer = answer

                if answer == "":
                    valid = False

            if not valid:
                raise ValidationError("Question answers are invalid.")

            if Application.objects.filter(
                form=form,
                eve_character=selected_character,
                character=detail,
                status=Application.STATUS_NEW,
            ).exists():
                raise IntegrityError("Application already exists.")

            application = Application.objects.create(
                form=form,
                eve_character=selected_character,
                character=detail,
                status=Application.STATUS_NEW,
            )

            responses = [
                ApplicationResponse(
                    question=question,
                    application=application,
                    answer=question.answer
                    if isinstance(question.answer, str)
                    else "\n".join(question.answer),
                )
                for question in questions
            ]

            ApplicationResponse.objects.bulk_create(responses, 100)
        except CharacterOwnership.DoesNotExist:
            logger.error(
                "User %s submitted an application to %s with non-owned or invalid selected character. [%d]",
                request.user,
                form,
                selected_character_id,
            )

            return HttpResponseBadRequest("Invalid form data")
        except ValidationError:
            logger.debug("Invalid question responses submitted.")
            messages.add_message(
                request, messages.ERROR, _("Please answer all questions correctly.")
            )
        else:
            messages.add_message(
                request, messages.SUCCESS, _("Application successfully submitted!")
            )
            return redirect("membertools:view", application.id)

    context = {
        "page_title": f"Apply for {form}",
        "form": form,
        "questions": questions,
        "corp": form.corp,
        "characters": characters,
        "main_character": request.user.profile.main_character,
    }
    return render(
        request,
        "membertools/app_create.html",
        hr_app_add_shared_context(request, context),
    )


@login_required
@permission_required("membertools.basic_access")
def hr_app_remove(request, app_id):
    logger.debug("hr_app_remove called by user %s for app id %s", request.user, app_id)
    app = get_object_or_404(Application, pk=app_id)
    if app.user == request.user:
        if app.status == app.STATUS_NEW:
            logger.info("User %s deleting their application %s", request.user, app)
            app.delete()
        else:
            logger.warning(
                "User %s attempting to delete their reviewed app %s", request.user, app
            )
            messages.add_message(
                request,
                messages.ERROR,
                _("You cannot delete an application that has already been reviewed."),
            )
    else:
        logger.warning("User %s not authorized to delete %s", request.user, app)
        return HttpResponseForbidden

    return redirect("membertools:index")


# Admin views
@login_required
@permission_required("membertools.admin_access")
def hr_admin_dashboard_view(request):
    user_review = (
        Application.objects.filter(reviewer__character_ownership__user=request.user)
        .filter(Q(status=Application.STATUS_WAIT) | Q(status=Application.STATUS_REVIEW))
        .order_by("status", "-submitted_on")
    )

    recruiter_forms = ApplicationForm.objects.get_forms_for_user(request.user)
    context = {
        "page_title": _("Dashboard"),
        "user_review_applications": user_review,
        "recruiter_forms": recruiter_forms,
    }
    return render(
        request,
        "membertools_admin/dashboard.html",
        hr_admin_add_shared_context(request, context),
    )


@login_required
@permission_required(["membertools.admin_access", "membertools.queue_admin_access"])
def hr_admin_queue_view(request):
    logger.debug("hr_admin_queue_view called by user %s", request.user)

    base_app_query = Application.objects.select_related(
        "eve_character__character_ownership__user", "form", "form__corp"
    )
    new_applications = base_app_query.filter(status=Application.STATUS_NEW)
    waiting_applications = base_app_query.filter(status=Application.STATUS_WAIT)
    review_applications = base_app_query.filter(status=Application.STATUS_REVIEW)

    # Always show users applications they have locked even if they lose access to them after locking.
    user_review = (
        Application.objects.filter(reviewer__character_ownership__user=request.user)
        .filter(Q(status=Application.STATUS_WAIT) | Q(status=Application.STATUS_REVIEW))
        .order_by("status", "-submitted_on")
    )
    if not request.user.is_superuser:
        user_forms = ApplicationForm.objects.get_forms_for_user(request.user)

        new_applications = new_applications.filter(form__in=user_forms)
        waiting_applications = waiting_applications.filter(form__in=user_forms)
        review_applications = review_applications.filter(form__in=user_forms)

    logger.debug(
        "Retrieved New: %d, Pending: %d, Review: %d, User Review: %d",
        new_applications.count(),
        waiting_applications.count(),
        review_applications.count(),
        user_review.count(),
    )
    context = {
        "page_title": _("Queues"),
        "new_applications": new_applications.order_by("submitted_on"),
        "waiting_applications": waiting_applications.order_by("submitted_on"),
        "review_applications": review_applications.order_by("submitted_on"),
        "user_review_applications": user_review,
    }

    return render(
        request,
        "membertools_admin/app_queue.html",
        hr_admin_add_shared_context(request, context),
    )


@login_required
@permission_required(
    ["membertools.admin_access", "membertools.application_admin_access"]
)
def hr_admin_archive_view(request):
    base_query = (
        Application.objects.select_related(
            "eve_character__character_ownership__user",
            "form",
            "form__corp",
            "form__title",
        )
        .filter(
            Q(decision=Application.DECISION_ACCEPT)
            | Q(decision=Application.DECISION_REJECT)
            | Q(decision=Application.DECISION_WITHDRAW)
        )
        .filter(form__in=ApplicationForm.objects.get_forms_for_user(request.user))
    )

    search = None

    if request.GET.get("search"):
        search_form = SearchForm(request.GET, placeholder=_("Application"))

        if search_form.is_valid():
            search = unicodedata.normalize(
                "NFKC", search_form.cleaned_data["search"]
            ).lower()
            logger.debug("Search: %s", search)
    else:
        search_form = SearchForm(placeholder=_("Application"))

    if search:
        applications = base_query.filter(
            Q(eve_character__character_name__icontains=search)
            | Q(
                eve_character__character_ownership__user__profile__main_character__character_name__icontains=search
            )
        ).order_by("-closed_on")
    else:
        applications = base_query.all().order_by("-closed_on")

    paginator = Paginator(applications, 50)

    try:
        page_number = int(request.GET.get("page"))
    except TypeError:
        page_number = 1

    context = {
        "page_title": _("Closed Applications"),
        "paginator": paginator,
        "applications": paginator.get_page(page_number),
        "application_delta_human": humanize.naturaldelta(MEMBERTOOLS_APP_ARCHIVE_TIME),
        "search_form": search_form,
    }

    return render(
        request,
        "membertools_admin/app_archive.html",
        hr_app_add_shared_context(request, context),
    )


@login_required
@permission_required(
    [
        "membertools.admin_access",
        "membertools.application_admin_access",
        "membertools.view_application",
    ]
)
def hr_admin_view(request, app_id, comment_form=None, edit_comment=None):
    logger.debug(f"hr_admin_view called by user {request.user} for app id {app_id}")
    app = get_object_or_404(Application, pk=app_id)

    try:
        member = app.main_character.next_character.member
    except ObjectDoesNotExist:
        member = None

    details, created = Character.objects.get_or_create(
        eve_character=app.eve_character,
        defaults={
            "eve_character": app.eve_character,
            "member": member,
        },
    )
    is_auditor = app.form.is_user_auditor(request.user)
    is_recruiter = app.form.is_user_recruiter(request.user)
    is_manager = app.form.is_user_manager(request.user)

    if is_auditor or is_recruiter:
        context = {
            "page_title": _("View Application") + f": {app.character}",
            "sub_title": app.form,
            "app": app,
            "char_detail": details,
            "corp_history": details.corporation_history.order_by("-record_id").all(),
            "checks": get_checks(app.user, app.eve_character, request),
            "responses": ApplicationResponse.objects.filter(application=app),
            "comments": Comment.objects.filter(application=app),
            "edit_comment": edit_comment,
            "comment_form": comment_form
            if comment_form
            else CommentForm(details, initial={"application": app}),
            "is_auditor": is_auditor,
            "is_recruiter": is_recruiter,
            "is_manager": is_manager,
            "search_form": SearchForm(placeholder=_("Application")),
            "search_form_action": reverse("membertools_admin:archive"),
            "base_url": reverse("membertools_admin:view", args=[app_id]),
            "show_add_comment": bool(
                edit_comment and request.user.has_perm("membertools:add_comment")
            ),
        }
        return render(
            request,
            "membertools_admin/app_view.html",
            hr_admin_add_shared_context(request, context),
        )
    else:
        logger.warn(f"User {request.user} not authorized to view {app}")
        return HttpResponseNotAllowed


@login_required
@permission_required(["membertools.admin_access", "membertools.character_admin_access"])
def hr_admin_char_detail_index(request):
    base_query = Character.objects.select_related(
        "eve_character", "eve_character__character_ownership__user"
    )
    search = None

    if request.GET.get("search"):
        search_form = SearchForm(request.GET, placeholder=_("Character"))

        if search_form.is_valid():
            search = unicodedata.normalize(
                "NFKC", search_form.cleaned_data["search"]
            ).lower()
            logger.debug("Search: %s", search)
    else:
        search_form = SearchForm(placeholder=_("Character"))

    if search:
        characters = base_query.filter(
            Q(eve_character__character_name__icontains=search)
            | Q(
                eve_character__character_ownership__user__profile__main_character__character_name__icontains=search
            )
        ).order_by("eve_character__character_name")
    else:
        characters = base_query.all().order_by("eve_character__character_name")

    paginator = Paginator(characters, 50)

    try:
        page_number = int(request.GET.get("page"))
    except TypeError:
        page_number = 1

    context = {
        "page_title": "Characters",
        "characters": paginator.get_page(page_number),
        "paginator": paginator,
        "search_form": search_form,
    }

    return render(
        request,
        "membertools_admin/char_detail_index.html",
        hr_admin_add_shared_context(request, context),
    )


@login_required
@permission_required(
    [
        "membertools.admin_access",
        "membertools.character_admin_access",
        "membertools.view_character",
    ]
)
def hr_admin_char_detail_view(
    request, char_detail_id, comment_form=None, edit_comment=None
):
    detail = get_object_or_404(Character, pk=char_detail_id)

    context = {
        "page_title": "View Character: {}".format(detail.eve_character),
        "sub_title": "Last Modified: {} \u2014 Expires: {}".format(
            date_format(
                detail.update_status.last_modified_on,
                format="SHORT_DATETIME_FORMAT",
                use_l10n=True,
            )
            if hasattr(detail, "update_status")
            else "Never",
            date_format(
                detail.update_status.expires_on,
                format="SHORT_DATETIME_FORMAT",
                use_l10n=True,
            )
            if hasattr(detail, "update_status")
            else "Never",
        ),
        "char_detail": detail,
        "corp_history": detail.corporation_history.order_by("-record_id").all(),
        "checks": get_checks(detail.user, detail.eve_character, request),
        "characters": get_user_characters(request, detail.eve_character),
        "comments": Comment.objects.filter(member=detail.member, character=detail),
        "edit_comment": edit_comment,
        "comment_form": comment_form
        if comment_form
        else CommentForm(detail, initial=edit_comment),
        "search_form": SearchForm(placeholder=_("Character")),
        "search_form_action": reverse("membertools_admin:char_detail_index"),
        "base_url": reverse(
            "membertools_admin:char_detail_view", args=[char_detail_id]
        ),
    }

    return render(
        request,
        "membertools_admin/char_detail_view.html",
        hr_admin_add_shared_context(request, context),
    )


@login_required
@permission_required(
    [
        "membertools.admin_access",
        "membertools.character_admin_access",
        "membertools.add_character",
    ]
)
def hr_admin_char_detail_lookup(request, char_id):
    char_id = int(char_id)

    if not char_id:
        return HttpResponseBadRequest()

    try:
        detail = Character.objects.get(eve_character__character_id=char_id)
    except Character.DoesNotExist:
        detail = None

    if not detail:
        char = get_object_or_404(
            EveCharacter,
            character_id=char_id,
        )

        owner = get_object_or_404(CharacterOwnership, character__character_id=char_id)
        member = getattr(owner.user, "next_member_detail", None)
        detail = Character.objects.create(eve_character=char, member=member)

        tasks.update_character.apply(args=[detail.id, True])

    return redirect("membertools_admin:char_detail_view", detail.id)


@login_required
@permission_required(
    [
        "membertools.admin_access",
        "membertools.application_admin_access",
        "membertools.delete_application",
    ]
)
def hr_admin_remove(request, app_id):
    logger.debug(f"hr_admin_remove called by user {request.user} for app id {app_id}")
    app = get_object_or_404(Application, pk=app_id)
    if not is_form_manager(app.form, request.user, "membertools.delete_application"):
        logger.warn(
            f"User {request.user} does not have permission to delete apps for {app.form}."
        )
        raise PermissionDenied
    logger.info(f"User {request.user} deleting {app}")
    app.delete()
    notify(
        app.user,
        "Application Deleted",
        message="Your application for %s was deleted." % app.form,
    )
    return redirect("membertools_admin:queue")


# Admin decision views


@login_required
@permission_required(
    [
        "membertools.admin_access",
        "membertools.application_admin_access",
        "membertools.view_application",
        "membertools.review_application",
    ]
)
def hr_admin_start_review_action(request, app_id):
    logger.debug(
        f"hr_admin_start_review called by user {request.user} for app id {app_id}"
    )
    app = get_object_or_404(Application, pk=app_id)
    is_recruiter = is_form_recruiter(app.form, request.user)
    is_manager = is_form_manager(app.form, request.user)

    if not is_recruiter:
        logger.warning(
            "User %s does not have permission to start review apps for %s.",
            request.user,
            app.form,
        )
        raise PermissionDenied
    if app.status == app.STATUS_CLOSED:
        messages.add_message(
            request,
            messages.ERROR,
            _("Can not Start Review on a closed application."),
        )
        return redirect("membertools_admin:view", app_id)
    if app.status == app.STATUS_REVIEW or app.status == app.STATUS_WAIT:
        if app.reviewer and app.reviewer.character_ownership.user != request.user:
            if not is_manager:
                logger.warning(
                    "User %s unable to start review %s: already being reviewed by %s",
                    request.user,
                    app,
                    app.reviewer,
                )
                messages.add_message(
                    request,
                    messages.ERROR,
                    _("Application is already under review by %(reviewer)s")
                    % {"reviewer": app.reviewer.profile.main_character},
                )
                return redirect("membertools_admin:view", app_id)

            logger.info("%s taking over %s for %s", request.user, app, app.reviewer)
            with transaction.atomic():
                ApplicationAction.objects.create_action(
                    app,
                    ApplicationAction.RELEASE,
                    app.reviewer,
                    None,
                    request.user.profile.main_character,
                )
                app.reviewer = request.user
                app.save()
                ApplicationAction.objects.create_action(
                    app, ApplicationAction.REVIEW, request.user.profile.main_character
                )
        else:
            logger.info(f"User %s resuming progress on %s", request.user, app)
            with transaction.atomic():
                app.last_status = app.status
                app.status = app.STATUS_REVIEW
                app.reviewer = request.user.profile.main_character
                app.save()
                ApplicationAction.objects.create_action(
                    app, ApplicationAction.REVIEW, request.user.profile.main_character
                )

    else:
        logger.info(f"User %s marking %s in progress", request.user, app)
        with transaction.atomic():
            app.last_status = app.status
            app.status = app.STATUS_REVIEW
            app.reviewer = request.user.profile.main_character
            app.save()
            ApplicationAction.objects.create_action(
                app, ApplicationAction.REVIEW, request.user.profile.main_character
            )
    return redirect("membertools_admin:view", app_id)


@login_required
@permission_required(
    [
        "membertools.admin_access",
        "membertools.application_admin_access",
        "membertools.view_application",
        "membertools.review_application",
    ]
)
def hr_admin_release_action(request, app_id):
    logger.debug(
        f"hr_admin_release_action called by user {request.user} for app id {app_id}"
    )
    app = get_object_or_404(Application, pk=app_id)
    is_recruiter = is_form_recruiter(app.form, request.user)
    is_manager = is_form_manager(app.form, request.user)
    reviewer_user = app.reviewer.character_ownership.user

    if not is_recruiter:
        logger.warning(
            "User %s does not have permission to release apps for %s.",
            request.user,
            app.form,
        )
        raise PermissionDenied

    if app.status == app.STATUS_CLOSED:
        messages.add_message(
            request,
            messages.ERROR,
            _("Can not release a closed application."),
        )
        return redirect("membertools_admin:view", app_id)

    # Can't release an app that isn't locked by reviewer.
    if not app.reviewer:
        messages.add_message(
            request,
            messages.ERROR,
            _("Can not release an application that isn't claimed by a reviewer."),
        )
        return redirect("membertools_admin:view", app_id)

    if not is_manager and reviewer_user != request.user:
        logger.warning("User %s attempted to release app_id %d", request.user, app_id)
        raise PermissionDenied

    if request.method == "POST":
        old_reviewer = app.reviewer
        with transaction.atomic():
            ApplicationAction.objects.create_action(
                app,
                ApplicationAction.RELEASE,
                app.reviewer,
                None,
                request.user.profile.main_character
                if reviewer_user != request.user
                else None,
            )
            app.reviewer = None
            app.status = app.last_status
            app.save()

        if reviewer_user != request.user:
            message = _(
                "Application released from %(reviewer)s and placed back into its last queue."
                % {"reviewer": old_reviewer}
            )
        else:
            message = _("Application released and placed back into its last queue.")

        messages.add_message(
            request,
            messages.SUCCESS,
            message,
        )

        return redirect("membertools_admin:queue")

    context = {
        "page_title": "Confirm Application Release",
        "message": _(
            "Are you sure you wish to release this application back to its last queue?"
        ),
        "cancel_url": "",
    }

    return render(
        request,
        "membertools_admin/confirmation.html",
        hr_admin_add_shared_context(request, context),
    )


@login_required
@permission_required(
    [
        "membertools.admin_access",
        "membertools.application_admin_access",
        "membertools.view_application",
        "membertools.review_application",
    ]
)
def hr_admin_claim_action(request, app_id):
    logger.debug(
        f"hr_admin_claim_action called by user {request.user} for app id {app_id}"
    )
    app = get_object_or_404(Application, pk=app_id)
    is_recruiter = is_form_recruiter(app.form, request.user)
    is_manager = is_form_manager(app.form, request.user)

    if not is_recruiter:
        logger.warning(
            "User %s does not have permission to claim apps for %s.",
            request.user,
            app.form,
        )
        raise PermissionDenied

    if app.status == app.STATUS_CLOSED:
        messages.add_message(
            request,
            messages.ERROR,
            _("Can not claim a closed application."),
        )
        return redirect("membertools_admin:view", app_id)

    # Can't claim an app that isn't locked by reviewer.
    if not app.reviewer:
        messages.add_message(
            request,
            messages.ERROR,
            _("Can not claim an application that isn't claimed by a reviewer."),
        )
        return redirect("membertools_admin:view", app_id)

    if app.reviewer.character_ownership.user == request.user:
        messages.add_message(
            request,
            messages.ERROR,
            _("Can not claim an application you are already reviewing."),
        )
        return redirect("membertools_admin:view", app_id)

    if not is_manager:
        logger.warning("User %s attempted to claim app_id %d", request.user, app_id)
        raise PermissionDenied

    if request.method == "POST":
        old_reviewer = app.reviewer
        with transaction.atomic():
            ApplicationAction.objects.create_action(
                app,
                ApplicationAction.RELEASE,
                app.reviewer,
                None,
                request.user.profile.main_character,
            )
            app.reviewer = request.user.profile.main_character
            app.status = app.STATUS_REVIEW
            app.save()
            ApplicationAction.objects.create_action(
                app, ApplicationAction.REVIEW, request.user.profile.main_character
            )

        messages.add_message(
            request,
            messages.SUCCESS,
            _("Application claimed from %(reviewer)s." % {"reviewer": old_reviewer}),
        )

        return redirect("membertools_admin:queue")

    context = {
        "page_title": "Confirm Application Release",
        "message": _(
            "Are you sure you wish to release this application back to its last queue?"
        ),
        "cancel_url": reverse("membertools_admin:view", args=[app_id]),
    }

    return render(
        request,
        "membertools_admin/confirmation.html",
        hr_admin_add_shared_context(request, context),
    )


@login_required
@permission_required(
    [
        "membertools.admin_access",
        "membertools.application_admin_access",
        "membertools.view_application",
        "membertools.approve_application",
    ]
)
@tokens_required(["esi-location.read_online.v1", "esi-ui.open_window.v1"])
def hr_admin_approve_action(request, tokens, app_id):
    logger.debug(
        "hr_admin_approve called by user %s for app id %s", request.user, app_id
    )
    app = get_object_or_404(Application, pk=app_id)
    is_recruiter = is_form_recruiter(app.form, request.user)
    is_manager = is_form_manager(app.form, request.user)
    is_override = request.user.profile.main_character != app.reviewer

    if not is_recruiter:
        logger.warning(
            "User %s does not have permission to accept apps for %s.",
            request.user,
            app.form,
        )
        return HttpResponseForbidden

    if is_override and not is_manager:
        logger.warning(
            "User %s does not have permission to override accept apps for %s.",
            request.user,
            app.form,
        )

        return HttpResponseForbidden

    if request.method == "POST":
        logger.info("User %s approving %s.", request.user, app)

        try:
            member = app.main_character.next_character.member
        except ObjectDoesNotExist:
            member = None

        with transaction.atomic():
            # Are we creating a new Member record for this character?
            if member is None:
                member = Member.objects.create(
                    first_main_character=app.eve_character,
                    main_character=app.eve_character,
                )
                logger.debug("Created new member record for %s", app.eve_character)
            char_detail = Character.objects.get(eve_character=app.eve_character)
            char_detail.member = member
            char_detail.save()

            app.status = Application.STATUS_PROCESSED
            app.decision = Application.DECISION_ACCEPT
            app.decision_on = timezone.now()

            # Title accepts have a few extra steps.
            if app.form.title:
                # Is this a new title for main?
                if (
                    app.form.title > member.awarded_title
                    and app.eve_character == app.main_character
                ):
                    member.awarded_title = app.form.title
                    member.save()

                char_detail.applied_title = app.form.title
                char_detail.save()

            app.save()
            ApplicationAction.objects.create_action(
                app,
                ApplicationAction.ACCEPT,
                request.user.profile.main_character
                if not is_override
                else app.reviewer,
                None,
                request.user.profile.main_character if is_override else None,
            )

        notify(
            app.user,
            "Application Accepted",
            message="Your application for %s has been approved." % app.form,
            level="success",
        )

        context = {
            "character": app.eve_character,
            "character_evelink": f'<font size="12" color="#ffd98d00"><a href="showinfo:1376//{app.eve_character.character_id}">{app.eve_character.character_name}</a></font>',
            "main_character": app.main_character,
            "officer": request.user.profile.main_character,
            "officer_evelink": f'<font size="12" color="#ffd98d00"><a href="showinfo:1376//{request.user.profile.main_character.character_id}">{request.user.profile.main_character.character_name}</a></font>',
        }
        token = tokens.require_valid().first()
        recipients = [app.eve_character.character_id]

        open_newmail_window_from_template(
            recipients=recipients,
            subject=app.form.accept_template_subject,
            template=app.form.accept_template_body,
            context=context,
            token=token,
        )

        messages.add_message(
            request,
            messages.SUCCESS,
            _("Application accepted. Check your EVE Client for accept mail window."),
        )

        return redirect("membertools_admin:queue")

    context = {
        "page_title": "Confirm Accept",
        "message": _(
            "Are you sure you wish to accept %(applicant)s's application to %(application)s?"
            % {"applicant": app.eve_character.character_name, "application": app.form}
        ),
        "cancel_url": reverse("membertools_admin:view", args=[app_id]),
    }

    return render(
        request,
        "membertools_admin/confirmation.html",
        hr_admin_add_shared_context(request, context),
    )


# Always allow reviewers to wait the applications they have under review.
@login_required
@permission_required(
    [
        "membertools.admin_access",
        "membertools.application_admin_access",
        "membertools.view_application",
        "membertools.review_application",
    ]
)
def hr_admin_wait_action(request, app_id):
    logger.debug(
        "hr_admin_wait_action called by user %s for app id %s", request.user, app_id
    )
    app = get_object_or_404(Application, pk=app_id)
    is_recruiter = is_form_recruiter(app.form, request.user)
    is_manager = is_form_manager(app.form, request.user)

    if not is_recruiter:
        logger.warning(
            "User %s does not have permission to wait apps for %s.",
            request.user,
            app.form,
        )
        return HttpResponseForbidden

    if not app.reviewer:
        messages.add_message(
            request,
            messages.INFO,
            _(
                "You cannot flag an application to wait that isn't being reviewed, sorcerer."
            ),
        )

    if not is_manager and request.user != app.reviewer.character_ownership.user:
        logger.warning(
            "User %s tied to wait while not reviewing %s [%d]",
            request.user,
            app,
            app.id,
        )

        return HttpResponseForbidden

    logger.info("User %s waiting %s", request.user, app)
    with transaction.atomic():
        app.status = app.STATUS_WAIT
        app.save()
        ApplicationAction.objects.create_action(
            app,
            ApplicationAction.WAIT,
            app.reviewer,
            None,
            request.user.profile.main_character
            if request.user != app.reviewer.character_ownership.user
            else None,
        )

    messages.add_message(
        request,
        messages.SUCCESS,
        _("Application has been successfully placed into your Wait queue."),
    )
    return redirect("membertools_admin:queue")


@login_required
@permission_required(
    [
        "membertools.admin_access",
        "membertools.application_admin_access",
        "membertools.view_application",
        "membertools.reject_application",
    ]
)
@tokens_required(["esi-location.read_online.v1", "esi-ui.open_window.v1"])
def hr_admin_reject_action(request, tokens, app_id):
    logger.debug(
        "hr_admin_reject_action called by user %s for app id %s.",
        request.user.username,
        app_id,
    )
    app = get_object_or_404(Application, pk=app_id)
    is_recruiter = is_form_recruiter(
        app.form, request.user, "membertools.reject_application"
    )
    is_manager = is_form_manager(app.form, request.user)
    is_override = request.user.profile.main_character != app.reviewer

    if not is_recruiter and not is_manager:
        logger.warning(
            "User %s does not have permission to reject apps for %s.",
            request.user,
            app.form,
        )
        return HttpResponseForbidden

    if is_override and not is_manager:
        logger.warning(
            "User %s does not have permission to override reject apps for %s.",
            request.user,
            app.form,
        )
        return HttpResponseForbidden

    if request.method == "POST":
        logger.info(f"User {request.user} rejecting {app}")
        with transaction.atomic():
            app.status = app.STATUS_PROCESSED
            app.decision = app.DECISION_REJECT
            app.closed = timezone.now()
            app.save()
            ApplicationAction.objects.create_action(
                app,
                ApplicationAction.REJECT,
                request.user.profile.main_character
                if not is_override
                else app.reviewer,
                None,
                request.user.profile.main_character if is_override else None,
            )
        notify(
            app.user,
            "Application Rejected",
            message="Your application to %s has been rejected." % app.form,
            level="danger",
        )

        context = {
            "character": app.eve_character,
            "character_evelink": f'<font size="12" color="#ffd98d00"><a href="showinfo:1376//{app.eve_character.character_id}">{app.eve_character.character_name}</a></font>',
            "main_character": app.main_character,
            "officer": request.user.profile.main_character,
            "officer_evelink": f'<font size="12" color="#ffd98d00"><a href="showinfo:1376//{request.user.profile.main_character.character_id}">{request.user.profile.main_character.character_name}</a></font>',
        }
        token = tokens.require_valid().first()
        recipients = [app.eve_character.character_id]

        open_newmail_window_from_template(
            recipients=recipients,
            subject=app.form.reject_template_subject,
            template=app.form.reject_template_body,
            context=context,
            token=token,
        )
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Application rejected. Check your EVE Client for reject mail window."),
        )

        return redirect("membertools_admin:queue")

    context = {
        "page_title": "Confirm Reject",
        "message": _("Are you sure you wish to reject this application?"),
        "cancel_url": reverse("membertools_admin:view", args=[app_id]),
    }

    return render(
        request,
        "membertools_admin/confirmation.html",
        hr_admin_add_shared_context(request, context),
    )


@login_required
@permission_required(
    [
        "membertools.admin_access",
        "membertools.application_admin_access",
        "membertools.view_application",
        "membertools.review_application",
    ]
)
def hr_admin_withdraw_action(request, app_id):
    logger.debug(
        "hr_admin_withdraw_action called by user %s for app id %s", request.user, app_id
    )
    app = get_object_or_404(Application, pk=app_id)
    is_recruiter = is_form_recruiter(app.form, request.user)
    is_manager = is_form_manager(app.form, request.user)
    is_override = request.user.profile.main_character != app.reviewer

    if not is_recruiter:
        logger.warning(
            "User %s does not have permission to withdraw apps for %s.",
            request.user,
            app.form,
        )
        return HttpResponseForbidden

    if is_override and not is_manager:
        logger.warning(
            "User %s does not have permission to override withdraw apps for %s.",
            request.user,
            app.form,
        )
        return HttpResponseForbidden

    if request.method == "POST":
        logger.info("User %s withdrawing %s.", request.user, app)
        with transaction.atomic():
            app.decision = app.DECISION_WITHDRAW
            app.status = app.STATUS_CLOSED
            app.decision_by = request.user.profile.main_character
            app.save()

            ApplicationAction.objects.create_action(
                app,
                ApplicationAction.WITHDRAW,
                app.reviewer,
                None,
                request.user.profile.main_character if is_override else None,
            )
            ApplicationAction.objects.create_action(
                app,
                ApplicationAction.CLOSE,
                app.reviewer,
                None,
                request.user.profile.main_character if is_override else None,
            )

        messages.add_message(
            request,
            messages.SUCCESS,
            _("Application withdrawn successfully."),
        )

        return redirect("membertools_admin:view", app.id)

    context = {
        "page_title": "Confirm Close",
        "message": _(
            "Are you sure you wish to Withdraw this application? Applicant will have to submit a new application."
        ),
        "cancel_url": reverse("membertools_admin:view", args=[app_id]),
    }

    return render(
        request,
        "membertools_admin/confirmation.html",
        hr_admin_add_shared_context(request, context),
    )


@login_required
@permission_required(
    [
        "membertools.admin_access",
        "membertools.application_admin_access",
        "membertools.view_application",
        "membertools.manage_applications",
    ]
)
@tokens_required(["esi-location.read_online.v1", "esi-ui.open_window.v1"])
def hr_admin_close_action(request, tokens, app_id):
    logger.debug(
        "hr_admin_close_action called by user %s for app id %s", request.user, app_id
    )
    app = get_object_or_404(Application, pk=app_id)
    is_manager = is_form_manager(app.form, request.user)

    if not is_manager:
        logger.warning(
            "User %s does not have permission to close apps for %s.",
            request.user,
            app.form,
        )
        return HttpResponseForbidden

    if request.method == "POST":
        logger.info("User %s closing %s.", request.user, app)
        with transaction.atomic():
            app.status = app.STATUS_CLOSED
            app.save()

            ApplicationAction.objects.create_action(
                app, ApplicationAction.CLOSE, request.user.profile.main_character
            )

        messages.add_message(
            request,
            messages.SUCCESS,
            _("Application closed successfully."),
        )

        return redirect("membertools_admin:view", app.id)

    context = {
        "page_title": "Confirm Close",
        "message": _(
            "Are you sure you wish to manually Close this application? This will remove any temporary permissions granted."
        ),
        "cancel_url": reverse("membertools_admin:view", args=[app_id]),
    }

    return render(
        request,
        "membertools_admin/confirmation.html",
        hr_admin_add_shared_context(request, context),
    )


# Comment functions


@login_required
@permission_required(
    [
        "membertools.admin_access",
        "membertools.application_admin_access",
        "membertools.view_application",
        "membertools.view_comment",
        "membertools.add_comment",
    ]
)
def hr_admin_comment_create(request, app_id):
    logger.debug("Comment Create: CDid: %s", app_id)

    if request.method != "POST":
        return HttpResponse("Method Not Allowed", status=405)

    application = get_object_or_404(Application, pk=app_id)

    form = CommentForm(
        application.character,
        data=request.POST,
    )

    if form.is_valid():
        form_app = form.instance.application
        if form_app and form_app.character != application.character:
            logger.warning(
                "User %s comment form application (App: %d, Char: %s) field has a different character than the application (App: %d, Char: %s)",
                request.user,
                form_app,
                form_app.character,
                application,
                application.character,
            )
            return HttpResponseBadRequest()

        comment: Comment = form.instance
        comment.poster = request.user.profile.main_character
        comment.member = application.member
        comment.character = application.character
        form.save()

        return redirect("membertools_admin:view", app_id)

    return hr_admin_view(request, app_id, comment_form=form)


@login_required
@permission_required(
    [
        "membertools.admin_access",
        "membertools.application_admin_access",
        "membertools.view_application",
        "membertools.view_comment",
        "membertools.add_comment",
    ]
)
def hr_admin_comment_edit(request, app_id, comment_id):
    logger.debug("Comment Edit: CDid: %s - Cid: %s", app_id, comment_id)

    application = get_object_or_404(Application, pk=app_id)
    comment = get_object_or_404(Comment, pk=comment_id)

    if request.method == "POST":
        form = CommentForm(application.character, instance=comment, data=request.POST)
        logger.debug("Valid: %s", form.is_valid())

        if form.is_valid():
            form_app = form.instance.application
            has_edit_comment = request.user.has_perm("membertools.change_comment")

            # Check if user can edit post first
            if (
                comment.poster.character_ownership.user != request.user
                and not has_edit_comment
            ):
                logger.warning(
                    "User %s attempted to edit another user's comment %d without edit permission.",
                    request.user,
                    comment.id,
                )
                return HttpResponseForbidden()
            elif (
                timezone.now() >= comment.created + MEMBERTOOLS_COMMENT_SELF_EDIT_TIME
                and not has_edit_comment
            ):
                messages.add_message(
                    request,
                    messages.ERROR,
                    _("You can not edit comments older than %s age.")
                    % humanize.naturaldelta(MEMBERTOOLS_COMMENT_SELF_EDIT_TIME),
                )
                return redirect("membertools_admin:view", app_id)

            # Now make sure the app field if provided is valid
            # Shouldn't be possible to meet this condition without modifying POST requests/form.
            if form_app and (
                form_app.character != application.character
                or not form_app.form.is_user_recruiter(request.user)
            ):
                logger.warning(
                    "User %s submitted an invalid/modified comment edit form. (Form App ID: %d, Form App Char: %s, App Char: %s, App Form: %s, Is Recruiter: %s)",
                    request.user,
                    form_app.id,
                    form_app.character,
                    application.character,
                    form_app.form,
                    form_app.form.is_user_recruiter(request.user),
                )

                return HttpResponseForbidden()

            form.save()

            messages.add_message(
                request, messages.SUCCESS, _("Comment has been saved successfully.")
            )

            return redirect("membertools_admin:view", app_id)
    else:
        form = CommentForm(application.character, instance=comment)

    return hr_admin_view(request, app_id, comment_form=form, edit_comment=comment)


@login_required
@permission_required(
    [
        "membertools.admin_access",
        "membertools.character_admin_access",
        "membertools.view_character",
        "membertools.view_comment",
        "membertools.add_comment",
    ]
)
def hr_admin_comment_delete(request, app_id, comment_id):
    logger.debug("Comment Delete: APPid: %s - Cid: %s", app_id, comment_id)

    application = get_object_or_404(Application, pk=app_id)
    comment = get_object_or_404(Comment, pk=comment_id)

    if not application.form.is_user_recruiter(request.user):
        logger.warning(
            "User %s called delete comment for an app from a form they don't recruit.",
            request.user,
        )
        return HttpResponseForbidden()

    has_delete_comment = request.user.has_perm(
        "membertools.delete_comment"
    ) & application.form.is_user_manager(request.user)

    if (
        comment.poster.character_ownership.user != request.user
        and not has_delete_comment
    ):
        logger.warning(
            "User %s attempted to delete another user's comment %d without delete permission.",
            request.user,
            comment.id,
        )
        return HttpResponseForbidden()

    if (
        timezone.now() >= comment.created + MEMBERTOOLS_COMMENT_SELF_DELETE_TIME
        and not has_delete_comment
    ):
        messages.add_message(
            request,
            messages.ERROR,
            _("You can not delete comments older than %s age.")
            % humanize.naturaldelta(MEMBERTOOLS_COMMENT_SELF_DELETE_TIME),
        )

        return redirect("membertools_admin:view", app_id)

    if request.method == "POST":
        logger.info(
            "User %s deleted comment_id %s on %s > %s",
            request.user,
            comment.id,
            comment.member,
            comment.character,
        )
        comment.delete()
        messages.add_message(
            request, messages.SUCCESS, _("Comment deleted successfully.")
        )

        return redirect("membertools_admin:view", app_id)

    context = {
        "page_title": "Confirm Comment Deletion",
        "message": _("Are you sure you wish to delete this comment?"),
        "cancel_url": reverse("membertools_admin:view", args=[app_id]),
    }

    return render(
        request,
        "membertools_admin/confirmation.html",
        hr_admin_add_shared_context(request, context),
    )


@login_required
@permission_required(
    [
        "membertools.admin_access",
        "membertools.character_admin_access",
        "membertools.view_character",
        "membertools.view_comment",
        "membertools.add_comment",
    ]
)
def hr_admin_char_detail_comment_create(request, char_id):
    logger.debug("Comment Create: CDid: %s", char_id)

    if request.method != "POST":
        return HttpResponse("Method Not Allowed", status=405)

    detail = get_object_or_404(Character, pk=char_id)

    form = CommentForm(detail, data=request.POST)

    logger.debug("Valid: %s", form.is_valid())

    if form.is_valid():
        comment: Comment = form.instance
        comment.poster = request.user.profile.main_character
        comment.member = detail.member
        comment.character = detail
        app = form.instance.application
        if (
            app
            and app.eve_character == detail.eve_character
            and app.form.is_user_recruiter(request.user)
        ) or not app:
            form.save()
        else:
            logger.warning(
                "User %s attempted to save a comment with invalid app. (App ID: %d, App Char: %s, Detail Char: %s)",
                request.user,
                app.id,
                app.character,
                detail.eve_character,
            )
            return HttpResponseForbidden()

        return redirect("membertools_admin:char_detail_view", char_id)

    return hr_admin_char_detail_view(request, char_id, comment_form=form)


@login_required
@permission_required(
    [
        "membertools.admin_access",
        "membertools.character_admin_access",
        "membertools.view_character",
        "membertools.view_comment",
        "membertools.add_comment",
    ]
)
def hr_admin_char_detail_comment_edit(request, char_id, comment_id):
    logger.debug("Comment Edit: CDid: %s - Cid: %s", char_id, comment_id)

    detail = get_object_or_404(Character, pk=char_id)
    comment = get_object_or_404(Comment, pk=comment_id)

    if request.method == "POST":
        form = CommentForm(detail, instance=comment, data=request.POST)
        logger.debug("Valid: %s", form.is_valid())

        if form.is_valid():
            app = form.instance.application
            has_edit_comment = request.user.has_perm("membertools.change_comment")

            # Check if user can edit post first
            if (
                comment.poster.character_ownership.user != request.user
                and not has_edit_comment
            ):
                logger.warning(
                    "User %s attempted to edit another user's comment %d without edit permission.",
                    request.user,
                    comment.id,
                )
                return HttpResponseForbidden()
            if (
                timezone.now() >= comment.created + MEMBERTOOLS_COMMENT_SELF_EDIT_TIME
                and not has_edit_comment
            ):
                messages.add_message(
                    request,
                    messages.ERROR,
                    _("You can not edit comments older than %s age.")
                    % humanize.naturaldelta(MEMBERTOOLS_COMMENT_SELF_EDIT_TIME),
                )
                return redirect("membertools_admin:char_detail_view", char_id)

            # Now make sure the app field if provided is valid
            # Shouldn't be possible to meet this condition without modifying POST requests/form.
            if app and (
                app.character != detail or not app.form.is_user_recruiter(request.user)
            ):
                logger.warning(
                    "User %s submitted an invalid/modified comment edit form. (App ID: %d, App Char: %s, Detail Char: %s, Form: %s, Is Recruiter: %s)",
                    request.user,
                    app.id,
                    app.character,
                    detail.eve_character,
                    app.form,
                    app.form.is_user_recruiter(request.user),
                )

                return HttpResponseForbidden()

            form.save()

            messages.add_message(
                request, messages.SUCCESS, _("Comment has been saved successfully.")
            )

            return redirect("membertools_admin:char_detail_view", char_id)
    else:
        form = CommentForm(detail, instance=comment)
    return hr_admin_char_detail_view(
        request, char_id, comment_form=form, edit_comment=comment
    )


@login_required
@permission_required(
    [
        "membertools.admin_access",
        "membertools.character_admin_access",
        "membertools.view_character",
        "membertools.view_comment",
        "membertools.add_comment",
    ]
)
def hr_admin_char_detail_comment_delete(request, char_id, comment_id):
    logger.debug("Comment Delete: CDid: %s - Cid: %s", char_id, comment_id)

    detail = get_object_or_404(Character, pk=char_id)
    comment = get_object_or_404(Comment, pk=comment_id)

    # TODO: Add delete confirmation...
    has_delete_comment = request.user.has_perm("membertools.delete_comment")

    if (
        comment.poster.character_ownership.user != request.user
        and not has_delete_comment
    ):
        logger.warning(
            "User %s attempted to delete another user's comment %d without delete permission.",
            request.user,
            comment.id,
        )
        return HttpResponseForbidden()

    if (
        timezone.now() >= comment.created + MEMBERTOOLS_COMMENT_SELF_DELETE_TIME
        and not has_delete_comment
    ):
        messages.add_message(
            request,
            messages.ERROR,
            _("You can not delete comments older than %s age.")
            % humanize.naturaldelta(MEMBERTOOLS_COMMENT_SELF_DELETE_TIME),
        )

        return redirect("membertools_admin:char_detail_view", char_id)

    if request.method == "POST":
        logger.info(
            "User %s deleted comment_id %s on %s > %s",
            request.user,
            comment.id,
            comment.member,
            comment.character,
        )
        comment.delete()
        messages.add_message(
            request, messages.SUCCESS, _("Comment deleted successfully.")
        )

        return redirect("membertools_admin:char_detail_view", char_id)

    context = {
        "page_title": "Confirm Comment Deletion",
        "message": _("Are you sure you wish to delete this comment?"),
        "cancel_url": reverse("membertools_admin:char_detail_view", args=[char_id]),
    }

    return render(
        request,
        "membertools_admin/confirmation.html",
        hr_admin_add_shared_context(request, context),
    )
