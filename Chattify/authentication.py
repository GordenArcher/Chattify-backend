from rest_framework_simplejwt.authentication import JWTAuthentication

class CookieOrHeaderAuthentication(JWTAuthentication):
    def authenticate(self, request):
        header_auth = super().authenticate(request)
        if header_auth:
            return header_auth 

        access_token = request.COOKIES.get("access_token")
        if not access_token:
            return None 
        
        try:
            validated_token = self.get_validated_token(access_token)
            user = self.get_user(validated_token)
            return (user, validated_token)
        except Exception as e:
            print(f"Token validation failed: {e}")  
            return None  
