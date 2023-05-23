# Standard Library
import string

# Alliance Auth
from esi.models import Token

from .app_settings import MEMBERTOOLS_TASKS_FOREGROUND_PRIORITY
from .tasks import open_newmail_window


class Context(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def open_newmail_window_from_template(
    recipients: list, subject: string, template: string, context: dict, token: Token
) -> bool:
    context = Context(context)

    subject = subject.format_map(context)
    body = template.format_map(context)

    return open_newmail_window.apply_async(
        args=(
            recipients,
            subject,
            body,
            token.id,
        ),
        priority=MEMBERTOOLS_TASKS_FOREGROUND_PRIORITY,
    )


def open_newmail_window_from_body(recipients, subject, body, token: Token) -> bool:
    pass
