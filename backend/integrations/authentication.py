from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings

class APIKeyAuthentication(BaseAuthentication):
    keyword = "Api-Key"

    def authenticate(self, request):
        # Prefer Authorization header with the `Api-Key <key>` scheme
        auth = request.headers.get("Authorization")

        if auth:
            if not auth.startswith(self.keyword):
                raise AuthenticationFailed("Formato inválido")

            key = auth[len(self.keyword):].strip()

            if key != settings.INTEGRATION_API_KEY:
                raise AuthenticationFailed("API Key inválida")

            return (None, key)

        # Fallback: accept X-API-KEY header (raw key value) for compatibility
        xkey = request.headers.get("X-API-KEY") or request.headers.get("X-Api-Key")
        if xkey:
            if xkey != settings.INTEGRATION_API_KEY:
                raise AuthenticationFailed("API Key inválida")
            return (None, xkey)

        # No authentication provided
        return None
