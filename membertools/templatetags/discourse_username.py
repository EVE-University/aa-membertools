# Standard Library
import re

# Django
from django import template
from django.template.defaultfilters import stringfilter

# Alliance Auth
from allianceauth.services.hooks import get_extension_logger

logger = get_extension_logger(__name__)
register = template.Library()


# This filter tries to cheaply approximate the Discourse Username that would be generated from a
# EVE character name
@register.filter
@stringfilter
def discourse_username(username) -> str:
    out = re.sub(r"[^\w.-]", "_", username)
    out = re.sub("[-_.]{2,}", "_", out)
    return out
