from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings

class APIKeyAuthentication(BaseAuthentication):
    keyword = "Api-Key"

    def authenticate(self, request):
        # Accept Authorization header with or without the 'Api-Key' prefix
        auth = request.headers.get("Authorization")

        if auth:
            # If startswith prefix, strip it; else, use as is
            if auth.startswith(self.keyword):
                key = auth[len(self.keyword):].strip()
            else:
                key = auth.strip()

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
