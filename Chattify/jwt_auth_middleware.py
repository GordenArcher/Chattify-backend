# In a file like jwt_auth_middleware.py
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
import logging
logger = logging.getLogger(__name__)
User = get_user_model()

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        headers = dict(scope.get("headers", {}))
        cookies = {}
        
        if b'cookie' in headers:
            cookie_header = headers[b'cookie'].decode()
            for cookie in cookie_header.split('; '):
                if '=' in cookie:
                    name, value = cookie.split('=', 1)
                    cookies[name] = value

        token = cookies.get('access_token')
        
        scope['user'] = AnonymousUser()
        
        if token:
            try:
                access_token = AccessToken(token)
                user = await self.get_user(access_token['user_id'])
                scope['user'] = user
                logger.info(f"Authenticated user: {user.username}")
            except Exception as e:
                logger.error(f"JWT auth error: {str(e)}")

        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return AnonymousUser()