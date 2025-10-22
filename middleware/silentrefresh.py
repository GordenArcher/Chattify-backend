from django.http import JsonResponse
import jwt
from datetime import datetime, timezone
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.tokens import RefreshToken, TokenError, AccessToken


class SilentRefreshJwtMiddleware(MiddlewareMixin):
    """
    Auto-refresh JWT access token from refresh token if:
      - access token is missing or expired
      - refresh token is valid

    Sets new access token cookie and updates request.META for DRF authentication.
    """

    ACCESS_COOKIE_NAME = "access_token"
    REFRESH_COOKIE_NAME = "refresh_token"
    REFRESH_THRESHOLD = 60 

    def process_request(self, request):
        access_token = request.COOKIES.get(self.ACCESS_COOKIE_NAME)
        refresh_token = request.COOKIES.get(self.REFRESH_COOKIE_NAME)

        if not refresh_token:
            return None  # no tokens at all — user not authenticated

        # If access token missing, try refresh immediately
        if not access_token:
            self._try_refresh(request, refresh_token)
            return None

        try:
            decoded = jwt.decode(
                access_token,
                settings.SIMPLE_JWT.get("SIGNING_KEY", settings.SECRET_KEY),
                algorithms=[settings.SIMPLE_JWT.get("ALGORITHM", "HS256")],
                options={"verify_exp": False}
            )
            exp_ts = decoded.get("exp")
            if not exp_ts:
                return None

            exp_dt = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
            now = datetime.now(timezone.utc)

            if exp_dt <= now or (exp_dt - now).total_seconds() < self.REFRESH_THRESHOLD:
                self._try_refresh(request, refresh_token)

        except jwt.InvalidTokenError:
            self._try_refresh(request, refresh_token)

        return None

    def _try_refresh(self, request, refresh_token_str):
        try:
            refresh = RefreshToken(refresh_token_str)
            new_access = str(refresh.access_token)
            request._new_access_token = new_access
            request.META["HTTP_AUTHORIZATION"] = f"Bearer {new_access}"

            if getattr(settings, "SIMPLE_JWT", {}).get("ROTATE_REFRESH_TOKENS", False):
                new_refresh = str(refresh)
                request._new_refresh_token = new_refresh

        except TokenError:
            request._clear_tokens = True

    def process_response(self, request, response):
        new_access = getattr(request, "_new_access_token", None)
        new_refresh = getattr(request, "_new_refresh_token", None)
        clear_tokens = getattr(request, "_clear_tokens", False)

        if clear_tokens:
            response.delete_cookie(self.ACCESS_COOKIE_NAME)
            response.delete_cookie(self.REFRESH_COOKIE_NAME)
            return response

        if new_access:
            response.set_cookie(
                key=self.ACCESS_COOKIE_NAME,
                value=new_access,
                httponly=True,
                secure=True,
                samesite="None",
                max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())
            )

        if new_refresh:
            response.set_cookie(
                key=self.REFRESH_COOKIE_NAME,
                value=new_refresh,
                httponly=True,
                secure=True,
                samesite="None",
                max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
            )

        return response
