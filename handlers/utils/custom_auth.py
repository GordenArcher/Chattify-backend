
from rest_framework_simplejwt.authentication import JWTAuthentication
from .auth_helpers import get_user_from_token

class CookieJWTAuthentication(JWTAuthentication):
    """
    DRF authentication class that reads JWT from cookies first, then Authorization header.
    """

    def get_raw_token(self, request):
        # Check cookies first
        token = request.COOKIES.get("access_token") or request.COOKIES.get("jwt")
        if token:
            return token
        # Fallback to header
        return super().get_raw_token(request)

    def authenticate(self, request):
        raw_token = self.get_raw_token(request)
        if not raw_token:
            return None
        user = get_user_from_token(raw_token)
        if user.is_anonymous:
            return None
        return (user, raw_token)
