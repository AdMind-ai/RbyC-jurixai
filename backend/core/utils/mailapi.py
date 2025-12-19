import requests
from django.conf import settings

MAILAPI_SEND_URL = "https://api.mailapi.dev/v1/email"


def send_template_email(
    *,
    to_email: str,
    subject: str,
    template_id: str,
    variables: dict,
):
    headers = {
        "Authorization": f"Bearer {settings.MAILAPI_API_KEY}",
        "Content-Type": "application/json",
    }
    
    print("MAILAPI_API_KEY:", settings.MAILAPI_API_KEY)

    payload = {
        "from": "help@admind.ai",
        "to": to_email,
        "subject": subject,
        "template_id": template_id,
        "template_data": variables,
        "reply_to": "help@admind.ai"
    }

    response = requests.post(
        MAILAPI_SEND_URL,
        json=payload,
        headers=headers
    )
    
    # Return structured result instead of raising so callers can inspect status
    try:
        return {
            "ok": 200 <= response.status_code < 300,
            "status_code": response.status_code,
            "text": response.text,
            "response": response,
        }
    except Exception:
        return {"ok": False, "status_code": None, "text": "Unknown error", "response": None}
