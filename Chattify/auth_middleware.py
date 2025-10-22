# Chattify/auth_middleware.py
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from urllib.parse import parse_qs
from handlers.utils.auth_helpers import get_user_from_token
import logging

logger = logging.getLogger(__name__)

class CookieJWTAuthentication(BaseMiddleware):
    """
    Channels middleware for authenticating WebSocket connections via JWT in cookies or query string.
    """

    def __init__(self, inner):
        super().__init__(inner)

    async def __call__(self, scope, receive, send):
        headers = dict(scope.get("headers", []))
        cookie_header = headers.get(b"cookie", b"").decode()

        cookies = {}
        if cookie_header:
            for cookie in cookie_header.split("; "):
                if "=" in cookie:
                    key, value = cookie.split("=", 1)
                    cookies[key] = value

        scope["cookies"] = cookies

        # Try cookies first, then query string
        token = cookies.get("access_token") or cookies.get("jwt")
        if not token:
            query_string = scope.get("query_string", b"").decode()
            if query_string:
                query_params = parse_qs(query_string)
                token = query_params.get("token", [None])[0]

        # Get user asynchronously
        if token:
            user = await database_sync_to_async(get_user_from_token)(token)
            scope["user"] = user
            logger.info(f"✅ WebSocket user authenticated: {user}")
        else:
            scope["user"] = AnonymousUser()
            logger.warning("❌ No token found for WebSocket, user is anonymous")

        return await super().__call__(scope, receive, send)
