import resend

from app.core.config import settings

resend.api_key = settings.RESEND_API_KEY


def send_deletion_warning_email(to_email: str, deletion_date: str) -> None:
    """deletion_date: pre-formatted human-readable string, e.g. "July 11, 2026"."""
    resend.Emails.send({
        "from": settings.EMAIL_FROM,
        "to": [to_email],
        "subject": "Your PersonnaPress account will be deleted in 7 days",
        "html": (
            f"<p>Your PersonnaPress trial ended 30 days ago. "
            f"Your account and all associated content will be permanently deleted on <strong>{deletion_date}</strong>.</p>"
            f"<p>To keep your account, subscribe before that date: "
            f"<a href='{settings.APP_URL}/account'>Subscribe now</a>.</p>"
            f"<p>If you have content you want to save, log in before {deletion_date} to copy it.</p>"
            f"<p>If you have questions, reply to this email.</p>"
        ),
    })


def send_verification_email(to_email: str, token: str) -> None:
    verification_url = f"{settings.APP_URL}/verify-email/confirm?token={token}"
    resend.Emails.send({
        "from": settings.EMAIL_FROM,
        "to": [to_email],
        "subject": "Verify your email address",
        "html": (
            f"<p>Click the link below to verify your email address. "
            f"This link expires in 24 hours.</p>"
            f"<p><a href=\"{verification_url}\">{verification_url}</a></p>"
        ),
    })
