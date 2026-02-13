import json
from urllib import error, request

from fastapi import HTTPException, status

from app.core.config import settings


SENDGRID_ENDPOINT = "https://api.sendgrid.com/v3/mail/send"


def send_password_setup_email(to_email: str, setup_link: str) -> None:
    if not settings.sendgrid_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SendGrid API key is not configured",
        )

    if not settings.email_from:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sender email is not configured",
        )

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": settings.email_from},
        "subject": "Set your LMS account password",
        "content": [
            {
                "type": "text/plain",
                "value": (
                    "Your account has been created by an administrator.\n\n"
                    "Use the link below to set your password:\n"
                    f"{setup_link}\n\n"
                    "This link expires soon and can only be used once."
                ),
            }
        ],
    }

    req = request.Request(
        SENDGRID_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.sendgrid_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req) as response:
            if response.status >= 400:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to send setup email",
                )
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to send setup email: {detail or exc.reason}",
        )
    except error.URLError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Email service unreachable: {exc.reason}",
        )
