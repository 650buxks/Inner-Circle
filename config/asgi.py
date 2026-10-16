"""ASGI entry point: the server (Daphne) loads `application` from here.

ASGI lets one server handle both normal web pages (HTTP) and live connections
(WebSockets).
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Set up Django before importing anything that uses models.
django_asgi_app = get_asgi_application()

from chats.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        # Only accept WebSockets from our own site, and log people in from
        # their session cookie (so consumers can use scope["user"]).
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
        ),
    }
)
