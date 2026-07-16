import json
import logging
import time

import httpx
from django.conf import settings


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
        self.timeout = getattr(settings, "VERA_API_TIMEOUT_SECONDS", 900)
        self.max_retries = getattr(settings, "VERA_API_MAX_RETRIES", 2)
        self.retry_backoff = getattr(settings, "VERA_API_RETRY_BACKOFF_SECONDS", 2)
        self.poll_interval = getattr(settings, "VERA_RUN_POLL_INTERVAL_SECONDS", 2)

        if not self.base_url or not self.api_key:
            raise VeraComplianceConfigurationError("Vera API is not configured.")

        self.client = httpx.Client(timeout=self.timeout)

    def _sleep_before_retry(self, attempt):
        delay = self.retry_backoff * (2 ** attempt)
        time.sleep(delay)

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _url(self, path):
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    def _request(self, method, path, **kwargs):
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.request(
                    method,
                    self._url(path),
                    headers=self._headers(),
                    **kwargs,
                )
                response.raise_for_status()
                return response
            except (httpx.HTTPError, ValueError) as exc:
                last_exception = exc
                logger.warning(
                    "Error calling Vera runs API attempt=%s/%s method=%s path=%s: %s",
                    attempt + 1,
                    self.max_retries + 1,
                    method,
                    path,
                    exc,
                )
                if attempt >= self.max_retries:
                    logger.exception("Error calling Vera runs API: %s", exc)
                    raise VeraComplianceServiceError("Error calling Vera runs API.") from exc
                self._sleep_before_retry(attempt)
        raise VeraComplianceServiceError("Error calling Vera runs API.") from last_exception

    def _build_run_payload(self, messages, session_key, instructions=None):
        message_items = list(messages or [])
        if not message_items:
            raise VeraComplianceServiceError("Vera run requires at least one message.")

        current_message = message_items[-1]
        input_text = current_message.get("content", "")
        conversation_history = [
            {
                "role": item.get("role", "user"),
                "content": item.get("content", ""),
            }
            for item in message_items[:-1]
            if item.get("content")
        ]

        payload = {
            "input": input_text,
            "session_id": session_key,
        }
        if instructions:
            payload["instructions"] = instructions
        if conversation_history:
            payload["conversation_history"] = conversation_history
        return payload

    def create_run(self, messages, session_key, instructions=None):
        payload = self._build_run_payload(messages, session_key, instructions=instructions)
        response = self._request("POST", "runs", json=payload)
        data = response.json()
        run_id = data.get("run_id")
        if not run_id:
            raise VeraComplianceServiceError("Vera run response did not include run_id.")
        return run_id

    def get_run(self, run_id):
        response = self._request("GET", f"runs/{run_id}")
        return response.json()

    def stop_run(self, run_id):
        response = self._request("POST", f"runs/{run_id}/stop")
        return response.json()

    def _poll_run_until_final(self, run_id):
        final_statuses = {"completed", "failed", "cancelled"}
        deadline = time.monotonic() + self.timeout

        while True:
            run = self.get_run(run_id)
            run_status = run.get("status")

            if run_status == "completed":
                return run.get("output") or ""

            if run_status in final_statuses:
                raise VeraComplianceServiceError(
                    f"Vera run finished with status {run_status}."
                )

            if time.monotonic() >= deadline:
                raise VeraComplianceServiceError("Vera run polling timed out.")

            time.sleep(self.poll_interval)

    def send_message(self, messages, session_key):
        run_id = self.create_run(messages, session_key)
        return self._poll_run_until_final(run_id)

    def stream_run_events(self, run_id):
        try:
            with self.client.stream(
                "GET",
                self._url(f"runs/{run_id}/events"),
                headers=self._headers(),
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    raw_payload = line.removeprefix("data:").strip()
                    if not raw_payload:
                        continue
                    try:
                        yield json.loads(raw_payload)
                    except ValueError:
                        logger.warning("Invalid Vera run event payload: %s", raw_payload)
        except httpx.HTTPError as exc:
            logger.exception("Error streaming Vera run events: %s", exc)
            raise VeraComplianceServiceError("Error streaming Vera run events.") from exc

    def stream_message(self, messages, session_key):
        for attempt in range(self.max_retries + 1):
            emitted_content = False
            emitted_text = ""
            run_id = None
            try:
                run_id = self.create_run(messages, session_key)
                final_output = ""

                for event in self.stream_run_events(run_id):
                    event_type = event.get("event")
                    if event_type == "message.delta":
                        delta = event.get("delta") or ""
                        if not delta:
                            continue
                        emitted_content = True
                        emitted_text += delta
                        yield delta
                    elif event_type == "run.completed":
                        final_output = event.get("output") or ""
                        if final_output and not emitted_content:
                            emitted_content = True
                            yield final_output
                        elif (
                            final_output
                            and emitted_text
                            and final_output.startswith(emitted_text)
                        ):
                            remaining_output = final_output[len(emitted_text):]
                            if remaining_output:
                                yield remaining_output
                        return
                    elif event_type in {"run.failed", "run.cancelled"}:
                        raise VeraComplianceServiceError(
                            f"Vera run event finished with status {event_type}."
                        )
                return
            except Exception as exc:
                if run_id:
                    try:
                        final_output = self._poll_run_until_final(run_id)
                        if final_output and not emitted_content:
                            yield final_output
                        elif final_output and emitted_text and final_output.startswith(emitted_text):
                            remaining_output = final_output[len(emitted_text):]
                            if remaining_output:
                                yield remaining_output
                        return
                    except Exception as poll_exc:
                        logger.warning(
                            "Error polling Vera run after stream failure run_id=%s: %s",
                            run_id,
                            poll_exc,
                        )

                logger.warning(
                    "Error streaming Vera run attempt=%s/%s emitted_content=%s: %s",
                    attempt + 1,
                    self.max_retries + 1,
                    emitted_content,
                    exc,
                )
                if emitted_content or attempt >= self.max_retries:
                    logger.exception("Error streaming Vera run: %s", exc)
                    raise VeraComplianceServiceError("Error streaming Vera run.") from exc
                self._sleep_before_retry(attempt)
