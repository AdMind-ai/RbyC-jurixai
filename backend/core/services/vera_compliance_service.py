import logging
import time

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
        self.timeout = getattr(settings, "VERA_API_TIMEOUT_SECONDS", 900)
        self.max_retries = getattr(settings, "VERA_API_MAX_RETRIES", 2)
        self.retry_backoff = getattr(settings, "VERA_API_RETRY_BACKOFF_SECONDS", 2)

        if not self.base_url or not self.api_key:
            raise VeraComplianceConfigurationError("Vera API is not configured.")

        # Vera exposes an OpenAI-compatible chat completions API.
        # The OpenAI SDK is used only as the HTTP client for Vera's base_url.
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout,
            max_retries=0,
        )

    def _sleep_before_retry(self, attempt):
        delay = self.retry_backoff * (2 ** attempt)
        time.sleep(delay)

    def send_message(self, messages, session_key):
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    stream=False,
                    messages=messages,
                    extra_headers={
                        "X-Hermes-Session-Key": session_key,
                    },
                )
                break
            except Exception as exc:
                last_exception = exc
                logger.warning(
                    "Error calling Vera compliance API attempt=%s/%s: %s",
                    attempt + 1,
                    self.max_retries + 1,
                    exc,
                )
                if attempt >= self.max_retries:
                    logger.exception("Error calling Vera compliance API: %s", exc)
                    raise VeraComplianceServiceError("Error calling Vera compliance API.") from exc
                self._sleep_before_retry(attempt)
        else:
            raise VeraComplianceServiceError("Error calling Vera compliance API.") from last_exception

        try:
            return response.choices[0].message.content or ""
        except (AttributeError, IndexError) as exc:
            logger.exception("Invalid Vera compliance API response: %s", exc)
            raise VeraComplianceServiceError("Invalid Vera compliance API response.") from exc

    def stream_message(self, messages, session_key):
        for attempt in range(self.max_retries + 1):
            emitted_content = False
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
                        emitted_content = True
                        yield content
                return
            except Exception as exc:
                logger.warning(
                    "Error streaming Vera compliance API attempt=%s/%s emitted_content=%s: %s",
                    attempt + 1,
                    self.max_retries + 1,
                    emitted_content,
                    exc,
                )
                if emitted_content or attempt >= self.max_retries:
                    logger.exception("Error streaming Vera compliance API: %s", exc)
                    raise VeraComplianceServiceError("Error streaming Vera compliance API.") from exc
                self._sleep_before_retry(attempt)
