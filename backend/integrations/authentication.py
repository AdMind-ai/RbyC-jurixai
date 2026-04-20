from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from integrations.models import IntegrationApiKey


class APIKeyAuthentication(BaseAuthentication):
    keyword = "Api-Key"

    def _authenticate_key(self, key):
        key_hash = IntegrationApiKey.hash_key(key)
        try:
            integration_key = (
                IntegrationApiKey.objects.select_related("client")
                .filter(
                    key_hash=key_hash,
                    active=True,
                    client__active=True,
                )
                .first()
            )
        except (OperationalError, ProgrammingError):
            integration_key = None

        if integration_key:
            return (None, integration_key)

        # Temporary fallback while existing environments are migrated.
        if key == settings.INTEGRATION_API_KEY:
            return (None, key)

        raise AuthenticationFailed("API Key invalida")

    def authenticate(self, request):
        auth = request.headers.get("Authorization")

        if auth:
            if auth.startswith(self.keyword):
                key = auth[len(self.keyword):].strip()
            else:
                key = auth.strip()
            return self._authenticate_key(key)

        xkey = request.headers.get("X-API-KEY") or request.headers.get("X-Api-Key")
        if xkey:
            return self._authenticate_key(xkey)

        return None
