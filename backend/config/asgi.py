"""
ASGI entrypoint — serves HTTP + WebSocket (Channels) for SafeCity.
"""

import os

from config.routing import application  # noqa: F401  (ASGI application object)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
