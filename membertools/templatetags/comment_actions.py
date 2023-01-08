from datetime import timedelta
from django import template
from django.contrib.auth.models import User
from django.template.defaultfilters import stringfilter
from django.utils import timezone
from allianceauth.services.hooks import get_extension_logger

from ..models import Comment
from ..app_settings import (
    MEMBERTOOLS_COMMENT_SELF_EDIT_TIME,
    MEMBERTOOLS_COMMENT_SELF_DELETE_TIME,
)

logger = get_extension_logger(__name__)
register = template.Library()


@register.inclusion_tag(
    "membertools_admin/partials/comment_actions_admin.html", takes_context=True
)
def comment_actions(context, comment: Comment):
    user: User = context["user"]
    edit_cutoff = timezone.now() - MEMBERTOOLS_COMMENT_SELF_EDIT_TIME
    del_cutoff = timezone.now() - MEMBERTOOLS_COMMENT_SELF_DELETE_TIME
    if user.has_perm("membertools.edit_comment") or (
        comment.poster == user and comment.created > edit_cutoff
    ):
        comment.can_edit = True
    else:
        comment.can_edit = False
    if user.has_perm("membertools.delete_comment") or (
        comment.poster == user and comment.created > del_cutoff
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
