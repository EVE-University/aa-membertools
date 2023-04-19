# Alliance Auth
from esi.clients import EsiClientProvider

from . import __version__

# TODO: Should we fix swagger spec?
esi = EsiClientProvider(app_info_text=f"aa-membertools v{__version__}")
