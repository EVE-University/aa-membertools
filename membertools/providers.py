# Standard Library
import os

# Alliance Auth
from esi.clients import EsiClientProvider

from . import __version__

SWAGGER_SPEC_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "swagger.json"
)

esi = EsiClientProvider(
    app_info_text=f"aa-membertools v{__version__}", spec_file=SWAGGER_SPEC_PATH
)
