
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth.models import AnonymousUser
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

def get_user_from_token(token):
    """
    Decode a JWT token and return a User instance.
    Returns AnonymousUser if token is invalid.
    """
    try:
        access_token = AccessToken(token)
        user = User.objects.get(id=access_token['user_id'])
        return user
    except Exception as e:
        logger.warning(f"Token validation failed: {e}")
        return AnonymousUser()
