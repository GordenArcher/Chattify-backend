"""
ASGI config for ChattifyBackend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application
from Chattify.auth_middleware import CookieJWTAuthentication
from Chattify.routing import websocket_urlpatterns  # adjust import as needed

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        CookieJWTAuthentication(
            URLRouter(websocket_urlpatterns)
        )
    ),
})

