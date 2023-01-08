from django.apps import AppConfig

from . import __version__


class MembertoolsConfig(AppConfig):
    name = "membertools"
    label = "membertools"
    verbose_name = f"Membertools v{__version__}"

    def ready(self):
        from . import signals
