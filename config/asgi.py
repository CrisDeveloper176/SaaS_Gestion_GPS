"""
ASGI config for fleet_backend project.
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django_asgi_app = get_asgi_application()

import apps.tracking.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": URLRouter(
        apps.tracking.routing.websocket_urlpatterns
    ),
})
