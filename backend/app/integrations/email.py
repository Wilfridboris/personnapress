import resend

from app.core.config import settings

resend.api_key = settings.RESEND_API_KEY


def send_verification_email(to_email: str, token: str) -> None:
    verification_url = f"{settings.APP_URL}/verify-email/confirm?token={token}"
    resend.Emails.send({
        "from": "PersonnaPress <noreply@personnapress.io>",
        "to": [to_email],
        "subject": "Verify your email address",
        "html": (
            f"<p>Click the link below to verify your email address. "
            f"This link expires in 24 hours.</p>"
            f"<p><a href=\"{verification_url}\">{verification_url}</a></p>"
        ),
    })
