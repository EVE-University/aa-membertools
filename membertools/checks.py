# Django
from django.apps import apps
from django.conf import settings
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

# Alliance Auth
from allianceauth.eveonline.models import EveCharacter
from allianceauth.services.hooks import get_extension_logger

logger = get_extension_logger(__name__)


class Check:
    # Constants
    CHECK_DISABLED = -1
    CHECK_FAILED = 0
    CHECK_PASSED = 1
    CHECK_WARNING = 2

    _check_methods = {
        "verified": "_do_check_verified",
        "memberaudit": "_do_check_memberaudit",
        "discord": "_do_check_discord",
        "mumble": "_do_check_mumble",
        "phpbb3": "_do_check_phpbb3",
        "euni_phpbb3": "_do_check_euni_phpbb3",
    }

    # Format:
    # {
    #     'memberaudit' : {
    #         'status' : AppCheck.CHECK_FAILED,
    #         'messages' : [
    #             { 'message' : 'Character Registered', 'status' : AppCheck.CHECK_PASSED },
    #             { 'message' : 'Character Not Updating', 'status' : AppCheck.CHECK_FAILED },
    #             { 'message' : 'Character Not Shared', 'status' : AppCheck.CHECK_FAILED },
    #         ]
    #     }
    # }

    app = None
    request = None
    _check_cache = {}

    def __init__(
        self,
        user: settings.AUTH_USER_MODEL,
        character: EveCharacter,
        request: HttpRequest,
    ):
        self._check_cache = {}
        self.user = user
        self.character = character
        self.request = request

    def _do_check(self, check):
        func = getattr(self, self._check_methods[check])
        func()

    @classmethod
    def get_instance(
        cls, user: settings.AUTH_USER_MODEL, character: EveCharacter, request
    ):
        if not hasattr(request, "check_instance_cache"):
            request.check_instance_cache = {}

        key = f"{user.id}_{character.id}"
        if key not in request.check_instance_cache:
            request.check_instance_cache[key] = cls(user, character, request)

        return request.check_instance_cache[key]

    def is_checked(
        self, check, user: settings.AUTH_USER_MODEL, character: EveCharacter
    ):
        if check not in self._check_methods:
            raise ValueError(f"{check} check is not supported.")

        return check in self._check_cache

    # pylint: disable=protected-access
    def check(
        self,
        check,
        user: settings.AUTH_USER_MODEL,
        character: EveCharacter,
        force=False,
    ):
        if check not in self._check_methods:
            raise ValueError(f"{check} check is not supported.")

        if force or not self.is_checked(check, user, character):
            self._do_check(check)

        return self._check_cache[check]

    # pylint: disable=import-error,import-outside-toplevel
    def _do_check_verified(self):
        title = _("Character Verification")
        status = None
        failed = 0
        messages = []

        CharacterOwnership = apps.get_model("authentication", "CharacterOwnership")

        try:
            owner = CharacterOwnership.objects.get(character=self.character)
        except CharacterOwnership.DoesNotExist:
            owner = None

        if owner and owner.user == self.user:
            status = self.CHECK_PASSED
            reason = _("Ownership has been ESI verified")
            messages.append({"message": reason, "status": self.CHECK_PASSED})
        else:
            status = self.CHECK_FAILED
            reason = _("Ownership needs to be verified")
            failed += 1
            messages.append({"message": reason, "status": self.CHECK_FAILED})

        self._check_cache["verified"] = {
            "title": title,
            "status": status,
            "reason": reason,
            "failed": failed,
            "messages": messages,
        }

    # pylint: disable=import-error,import-outside-toplevel,broad-except
    def _do_check_memberaudit(self):
        title = _("Member Audit")
        status = self.CHECK_PASSED
        reason = _("All checks passed")
        messages = []
        failed = 0

        if apps.is_installed("memberaudit"):
            Character = apps.get_model("memberaudit", "Character")

            query = Character.objects.filter(eve_character=self.character)

            if query.exists():
                char = query.get()
                messages.append(
                    {
                        "message": _("Character is registered"),
                        "status": self.CHECK_PASSED,
                    }
                )
            else:
                char = None
                status = self.CHECK_FAILED
                reason = _(
                    "Character is not registered, please add this character in Member Audit"
                )
                failed += 1
                messages.append({"message": reason, "status": self.CHECK_FAILED})

            if char is not None:
                update_status = char.is_update_status_ok()

                if update_status:
                    messages.append(
                        {
                            "message": _(
                                "Character details have successfully been updated"
                            ),
                            "status": self.CHECK_PASSED,
                        }
                    )
                elif update_status is False:
                    status = self.CHECK_FAILED
                    reason = _(
                        "Invalid ESI token, please delete and re-register character"
                    )
                    failed += 1
                    messages.append({"message": reason, "status": self.CHECK_FAILED})
                else:
                    status = self.CHECK_WARNING
                    reason = _("Character details are being updated")
                    messages.append({"message": reason, "status": self.CHECK_WARNING})

            if char is not None and char.is_shared:
                messages.append(
                    {
                        "message": _("Character details are shared with recruiters"),
                        "status": self.CHECK_PASSED,
                    }
                )
            else:
                status = self.CHECK_FAILED
                reason = _("Character details need to be shared with recruiters")
                failed += 1
                messages.append({"message": reason, "status": self.CHECK_FAILED})

            if failed > 1:
                reason = _("Multiple checks failed")

        else:
            status = self.CHECK_DISABLED
            reason = _("Member Audit is not installed or enabled")
            messages.append({"message": reason, "status": self.CHECK_FAILED})

        self._check_cache["memberaudit"] = {
            "title": title,
            "status": status,
            "reason": reason,
            "failed": failed,
            "messages": messages,
        }

    # pylint: disable=import-error,import-outside-toplevel,broad-except
    def _do_check_discord(self):
        title = _("Discord")
        status = self.CHECK_PASSED
        reason = _("All checks passed")
        failed = 0
        messages = []

        if apps.is_installed("allianceauth.services.modules.discord"):
            DiscordUser = apps.get_model("discord", "DiscordUser")

            query = DiscordUser.objects.filter(user=self.user)

            if query.exists():
                discord = query.get()
                messages.append(
                    {
                        "message": _("Discord is linked"),
                        "status": self.CHECK_PASSED,
                    }
                )
            else:
                discord = None
                status = self.CHECK_FAILED
                reason = _("Discord is not linked. Please link Discord in Services")
                messages.append({"message": reason, "status": self.CHECK_FAILED})
                failed += 1

            if discord and discord.activated:
                messages.append(
                    {
                        "message": _("Discord account is active"),
                        "status": self.CHECK_PASSED,
                    }
                )
            else:
                status = self.CHECK_FAILED
                reason = _(
                    "Discord account is not active, please reset Discord link in Services"
                )
                failed += 1
                messages.append({"message": reason, "status": self.CHECK_FAILED})

            if failed > 1:
                reason = _("Multiple checks failed")
        else:
            status = self.CHECK_DISABLED
            reason = _("Discord service is not installed or enabled")
            messages.append(
                {
                    "message": reason,
                    "status": self.CHECK_FAILED,
                }
            )

        self._check_cache["discord"] = {
            "title": title,
            "status": status,
            "reason": reason,
            "failed": failed,
            "messages": messages,
        }

        # pylint: disable=import-error,import-outside-toplevel,broad-except

    def _do_check_mumble(self):
        title = _("Mumble")
        status = self.CHECK_PASSED
        reason = _("All checks passed")
        failed = 0
        messages = []

        if apps.is_installed("allianceauth.services.modules.mumble"):
            MumbleUser = apps.get_model("mumble", "MumbleUser")

            query = MumbleUser.objects.filter(user=self.user)

            if query.exists():
                messages.append(
                    {
                        "message": _("Mumble account is active"),
                        "status": self.CHECK_PASSED,
                    }
                )
            else:
                status = self.CHECK_FAILED
                reason = _(
                    "Mumble account is not active, please reset account in Services"
                )
                failed += 1
                messages.append({"message": reason, "status": self.CHECK_FAILED})
        else:
            status = self.CHECK_DISABLED
            reason = _("Mumble service is not enabled")
            messages.append({"message": reason, "status": self.CHECK_FAILED})

        self._check_cache["mumble"] = {
            "title": title,
            "status": status,
            "reason": reason,
            "failed": failed,
            "messages": messages,
        }

    def _do_check_phpbb3(self):
        title = _("phpBB3")
        status = self.CHECK_PASSED
        reason = _("All checks passed")
        failed = 0
        messages = []

        if apps.is_installed("allianceauth.services.modules.phpbb3"):
            Phpbb3User = apps.get_model("phpbb3", "Phpbb3User")

            query = Phpbb3User.objects.filter(user=self.user)

            if query.exists():
                messages.append(
                    {
                        "message": _("PhpBB3 (Forum) account is active"),
                        "status": self.CHECK_PASSED,
                    }
                )
            else:
                status = self.CHECK_FAILED
                reason = _(
                    "PhpBB3 (Forum) account is not active, please reset account in Services"
                )
                failed += 1
                messages.append({"message": reason, "status": self.CHECK_FAILED})
        else:
            status = self.CHECK_DISABLED
            reason = _("PhpBB3 service is not enabled")
            messages.append({"message": reason, "status": self.CHECK_FAILED})

        self._check_cache["phpbb3"] = {
            "title": title,
            "status": status,
            "reason": reason,
            "failed": failed,
            "messages": messages,
        }

    def _do_check_euni_phpbb3(self):
        title = _("Forum")
        status = self.CHECK_PASSED
        reason = _("All checks passed")
        failed = 0
        messages = []

        if apps.is_installed("eunicore.phpbb3"):
            Phpbb3User = apps.get_model("euni_phpbb3", "Phpbb3User")

            query = Phpbb3User.objects.filter(user=self.user)

            if query.exists():
                messages.append(
                    {
                        "message": _("Forum account is active"),
                        "status": self.CHECK_PASSED,
                    }
                )
            else:
                status = self.CHECK_FAILED
                reason = _(
                    "Forum account is not active, please reset account in Services"
                )
                failed += 1
                messages.append({"message": reason, "status": self.CHECK_FAILED})
        else:
            status = self.CHECK_DISABLED
            reason = _("PhpBB3 service is not enabled")
            messages.append({"message": reason, "status": self.CHECK_FAILED})

        self._check_cache["euni_phpbb3"] = {
            "title": title,
            "status": status,
            "reason": reason,
            "failed": failed,
            "messages": messages,
        }
