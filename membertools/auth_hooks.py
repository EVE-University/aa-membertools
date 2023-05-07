# Alliance Auth
from allianceauth import hooks
from allianceauth.services.hooks import MenuItemHook, UrlHook, get_extension_logger

from . import urls_admin, urls_app
from .app_settings import (
    MEMBERTOOLS_ADMIN_BASE_URL,
    MEMBERTOOLS_ADMIN_MENU_TITLE,
    MEMBERTOOLS_APP_BASE_URL,
    MEMBERTOOLS_APP_MENU_TITLE,
)
from .models import Application, TitleFilter

logger = get_extension_logger(__name__)


class ApplicationsMenu(MenuItemHook):
    def __init__(self):
        MenuItemHook.__init__(
            self,
            MEMBERTOOLS_APP_MENU_TITLE,
            "fas fa-hat-wizard",
            "membertools:index",
            1002,
            navactive=["membertools:"],
        )

    def render(self, request):
        if request.user.has_perm("membertools.basic_access"):
            app_count = Application.objects.recent_finished_apps_count_for_user(
                request.user
            )
            self.count = app_count if app_count and app_count > 0 else None
            return MenuItemHook.render(self, request)
        return ""


class AdminMenu(MenuItemHook):
    def __init__(self):
        MenuItemHook.__init__(
            self,
            MEMBERTOOLS_ADMIN_MENU_TITLE,
            "fas fa-frown",
            "membertools_admin:index",
            1003,
            navactive=["membertools_admin:"],
        )

    def render(self, request):
        if request.user.has_perm("membertools.admin_access"):
            app_count = Application.objects.new_application_count_for_admin_user(
                request.user
            )
            self.count = app_count if app_count else None
            if app_count >= 2:
                self.classes = "fas fa-frown text-warning"
            if app_count >= 5:
                self.classes = "fas fa-angry text-danger"
            return MenuItemHook.render(self, request)

        logger.debug(
            "admin_access: %s - queue_admin_access: %s",
            request.user.has_perm("membertools.admin_access"),
            request.user.has_perm("membertools.queue_admin_access"),
        )
        return ""


@hooks.register("menu_item_hook")
def register_menu():
    return ApplicationsMenu()


@hooks.register("menu_item_hook")
def register_admin_menu():
    return AdminMenu()


class ApplicationsUrls(UrlHook):
    def __init__(self):
        UrlHook.__init__(
            self,
            urls_app,
            "membertools",
            rf"^{MEMBERTOOLS_APP_BASE_URL}/",
        )


class AdminUrls(UrlHook):
    def __init__(self):
        UrlHook.__init__(
            self,
            urls_admin,
            "membertools_admin",
            rf"^{MEMBERTOOLS_ADMIN_BASE_URL}/",
        )


@hooks.register("url_hook")
def register_app_url():
    return ApplicationsUrls()


@hooks.register("url_hook")
def register_adm_url():
    return AdminUrls()


@hooks.register("secure_group_filters")
def register_sg_filters():
    return [TitleFilter]
