import logging

from django.conf import settings
from openai import OpenAI


logger = logging.getLogger(__name__)


class VeraComplianceConfigurationError(Exception):
    pass


class VeraComplianceServiceError(Exception):
    pass


def build_vera_session_key(user, session_context=None):
    context = session_context or {}
    organization_id = (
        context.get("organization_id")
        or getattr(settings, "VERA_DEFAULT_ORGANIZATION_ID", None)
        or "rbyc"
    )
    client_id = (
        context.get("client_id")
        or getattr(settings, "VERA_DEFAULT_CLIENT_ID", None)
        or "default-client"
    )
    matter_id = (
        context.get("matter_id")
        or getattr(settings, "VERA_DEFAULT_MATTER_ID", None)
        or "default-matter"
    )
    user_id = context.get("user_id") or getattr(user, "pk", None) or "anonymous"

    return f"vera:{organization_id}:{client_id}:{matter_id}:{user_id}"


class VeraComplianceService:
    def __init__(self):
        self.base_url = getattr(settings, "VERA_API_BASE_URL", None)
        self.api_key = getattr(settings, "VERA_API_SERVER_KEY", None)
        self.model = getattr(settings, "VERA_API_MODEL", "vera-compliance")

        if not self.base_url or not self.api_key:
            raise VeraComplianceConfigurationError("Vera API is not configured.")

        # Vera exposes an OpenAI-compatible chat completions API.
        # The OpenAI SDK is used only as the HTTP client for Vera's base_url.
        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)

    def send_message(self, messages, session_key):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                stream=False,
                messages=messages,
                extra_headers={
                    "X-Hermes-Session-Key": session_key,
                },
            )
        except Exception as exc:
            logger.exception("Error calling Vera compliance API: %s", exc)
            raise VeraComplianceServiceError("Error calling Vera compliance API.") from exc

        try:
            return response.choices[0].message.content or ""
        except (AttributeError, IndexError) as exc:
            logger.exception("Invalid Vera compliance API response: %s", exc)
            raise VeraComplianceServiceError("Invalid Vera compliance API response.") from exc

    def stream_message(self, messages, session_key):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                stream=True,
                messages=messages,
                extra_headers={
                    "X-Hermes-Session-Key": session_key,
                },
            )

            for chunk in response:
                choices = getattr(chunk, "choices", None) or []
                if not choices:
                    continue

                delta = getattr(choices[0], "delta", None)
                content = getattr(delta, "content", None)
                if content:
                    yield content
        except Exception as exc:
            logger.exception("Error streaming Vera compliance API: %s", exc)
            raise VeraComplianceServiceError("Error streaming Vera compliance API.") from exc
