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

        # Fallback to Authorization header
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if not auth_header:
            return None
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        return parts[1]

    def authenticate(self, request):
        raw_token = self.get_raw_token(request)
        if not raw_token:
            return None
        user = get_user_from_token(raw_token)
        if user.is_anonymous:
            return None
        return (user, raw_token)
