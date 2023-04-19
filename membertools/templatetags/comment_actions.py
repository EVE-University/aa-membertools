# Django
from django import template
from django.contrib.auth.models import User
from django.utils import timezone

# Alliance Auth
from allianceauth.services.hooks import get_extension_logger

from ..app_settings import (
    MEMBERTOOLS_COMMENT_SELF_DELETE_TIME,
    MEMBERTOOLS_COMMENT_SELF_EDIT_TIME,
)
from ..models import Comment

logger = get_extension_logger(__name__)
register = template.Library()


@register.inclusion_tag(
    "membertools_admin/partials/comment_actions.html", takes_context=True
)
def comment_actions(context, comment: Comment):
    user: User = context["user"]
    edit_cutoff = timezone.now() - MEMBERTOOLS_COMMENT_SELF_EDIT_TIME
    del_cutoff = timezone.now() - MEMBERTOOLS_COMMENT_SELF_DELETE_TIME
    if user.has_perm("membertools.change_comment") or (
        comment.poster == user.profile.main_character and comment.created > edit_cutoff
    ):
        comment.can_edit = True
    else:
        comment.can_edit = False
    if user.has_perm("membertools.delete_comment") or (
        comment.poster == user.profile.main_character and comment.created > del_cutoff
    ):
        comment.can_delete = True
    else:
        comment.can_delete = False

    logger.debug(
        "[%d] %s - CD: %s CE: %s",
        comment.id,
        user,
        comment.can_delete,
        comment.can_edit,
    )
    context.update({"comment": comment})
    return context
