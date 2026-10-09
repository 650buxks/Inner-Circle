"""ASGI entry point: the server (Daphne) loads `application` from here.

ASGI lets one server handle both normal web pages (HTTP) and live connections
(WebSockets). WebSocket routes for real-time chat get added in Phase 4.
"""

import os

from channels.routing import ProtocolTypeRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Set up Django before importing anything that uses models.
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        # "websocket": ... (Phase 4)
    }
)
