from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model

# Context: I used session cookies before, but now I want to use JWT tokens for authentication.
# This class was generated from OpenAI, ChatGPT o1-mini
# Prompt: 'Can you make a middleware class to authenticate users using JWT tokens?'
User = get_user_model()
class JWTAuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        access_token = request.COOKIES.get('access_token')
        if not access_token:
            request.user = AnonymousUser()
            return

        try:
            token = AccessToken(access_token)
            user_id = token['user_id']
            user = User.objects.get(id=user_id)
            request.user = user
        except Exception:
            request.user = AnonymousUser()

