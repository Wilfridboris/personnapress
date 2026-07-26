import html as _html
import logging

import resend

from app.core.config import settings

resend.api_key = settings.RESEND_API_KEY

logger = logging.getLogger(__name__)


def add_contact_to_audience(email: str, source: str) -> None:
    """
    Adds a contact to the Resend audience. Fire-and-forget — caller must
    wrap in asyncio.to_thread and swallow exceptions.
    """
    if not settings.RESEND_API_KEY:
        logger.warning("[audience] RESEND_API_KEY not set — skipping contact add")
        return
    segment_id = settings.RESEND_SEGMENT_ID
    if not segment_id:
        logger.warning("[audience] RESEND_SEGMENT_ID not set — skipping contact add")
        return
    resend.Contacts.create({
        "email": email,
        "unsubscribed": False,
        "segments": [{"id": segment_id}],
        "properties": {"source": source},
    })


def build_email_html(
    body_html: str,
    cta_text: str | None = None,
    cta_url: str | None = None,
    heading: str | None = None,
) -> str:
    """
    Wraps body_html in the PersonnaPress branded email template.
    body_html: pre-formatted HTML paragraphs (<p> tags).
    heading: optional bold section heading rendered above body_html.
    cta_text + cta_url: optional CTA button (both must be provided together).
    """
    cta_block = ""
    if cta_text and cta_url:
        safe_url = _html.escape(cta_url, quote=True)
        safe_text = _html.escape(cta_text)
        cta_block = f"""
          <tr>
            <td style="padding: 24px 40px 0 40px;">
              <a href="{safe_url}"
                 style="display: inline-block; background-color: #111111; color: #ffffff;
                        font-family: Arial, Helvetica, sans-serif; font-size: 14px;
                        font-weight: bold; text-decoration: none; padding: 12px 24px;
                        border: 1px solid #111111;
                        box-shadow: 4px 4px 0px 0px #111111;">
                {safe_text}
              </a>
            </td>
          </tr>"""

    heading_block = ""
    if heading:
        safe_heading = _html.escape(heading)
        heading_block = f"""
          <tr>
            <td style="padding: 0 40px 16px 40px;">
              <h2 style="margin: 0; font-family: Georgia, 'Times New Roman', serif;
                         font-size: 22px; font-weight: bold; color: #111111;
                         line-height: 1.3;">
                {safe_heading}
              </h2>
            </td>
          </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #F9F9F6;
             font-family: Arial, Helvetica, sans-serif;">
  <table role="presentation" cellpadding="0" cellspacing="0" border="0"
         width="100%" style="background-color: #F9F9F6;">
    <tr>
      <td align="center" style="padding: 40px 16px;">

        <table role="presentation" cellpadding="0" cellspacing="0" border="0"
               width="600" style="max-width: 600px; width: 100%;
                                  background-color: #F9F9F6;
                                  border: 1px solid #E5E5E5;">

          <!-- Header: Wordmark -->
          <tr>
            <td style="padding: 28px 40px; border-bottom: 1px solid #E5E5E5;">
              <span style="font-family: Georgia, 'Times New Roman', serif;
                           font-size: 20px; font-weight: bold; color: #111111;
                           letter-spacing: -0.01em;">
                PersonnaPress
              </span>
            </td>
          </tr>

          <!-- Body: heading (optional) -->
          {heading_block}

          <!-- Body: content -->
          <tr>
            <td style="padding: 32px 40px 0 40px;
                       font-family: Arial, Helvetica, sans-serif;
                       font-size: 16px; color: #111111; line-height: 1.6;">
              {body_html}
            </td>
          </tr>

          <!-- CTA button (optional) -->
          {cta_block}

          <!-- Divider -->
          <tr>
            <td style="padding: 32px 40px 0 40px;">
              <hr style="border: none; border-top: 1px solid #E5E5E5; margin: 0;">
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 24px 40px 32px 40px;
                       font-family: Arial, Helvetica, sans-serif;
                       font-size: 12px; color: #555555; line-height: 1.5;">
              <p style="margin: 0 0 8px 0;">
                <strong style="font-family: Georgia, 'Times New Roman', serif;
                               color: #111111;">PersonnaPress</strong>
              </p>
              <p style="margin: 0 0 8px 0;">
                Questions? Email
                <a href="mailto:support@personnapress.com"
                   style="color: #111111; text-decoration: underline;">
                  support@personnapress.com
                </a>
              </p>
              <!-- Social links placeholder - will be expanded in a future story -->
              <p style="margin: 0; color: #555555;">
                Follow us:
                <a href="https://x.com/personnapress"
                   style="color: #555555; text-decoration: none; margin-right: 8px;">X / Twitter</a>
                <a href="https://linkedin.com/company/personnapress"
                   style="color: #555555; text-decoration: none;">LinkedIn</a>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def send_verification_email(to_email: str, token: str) -> None:
    verification_url = f"{settings.APP_URL}/verify-email/confirm?token={token}"
    safe_url = _html.escape(verification_url, quote=True)
    html = build_email_html(
        body_html=(
            f"<p>Click the link below to verify your email address. "
            f"This link expires in 24 hours.</p>"
            f"<p style=\"font-size: 13px; color: #555555; word-break: break-all;\">"
            f"<a href=\"{safe_url}\" style=\"color: #555555;\">{safe_url}</a></p>"
        ),
        cta_text="Verify email address",
        cta_url=verification_url,
    )
    resend.Emails.send({
        "from": settings.EMAIL_FROM,
        "to": [to_email],
        "reply_to": "support@personnapress.com",
        "subject": "Verify your email address",
        "html": html,
    })


def send_deletion_warning_email(to_email: str, deletion_date: str) -> None:
    """deletion_date: pre-formatted human-readable string, e.g. "July 11, 2026"."""
    html = build_email_html(
        body_html=(
            f"<p>Your PersonnaPress trial ended 30 days ago. "
            f"Your account and all associated content will be permanently deleted "
            f"on <strong>{deletion_date}</strong>.</p>"
            f"<p>To keep your account, subscribe before that date.</p>"
            f"<p>If you have content you want to save, log in before {deletion_date} to copy it.</p>"
        ),
        cta_text="Subscribe now",
        cta_url=f"{settings.APP_URL}/account",
    )
    resend.Emails.send({
        "from": settings.EMAIL_FROM,
        "to": [to_email],
        "reply_to": "support@personnapress.com",
        "subject": "Your PersonnaPress account will be deleted in 7 days",
        "html": html,
    })


def send_reengagement_email(to_email: str, first_name: str | None) -> None:
    salutation = f"Hey {first_name}," if first_name else "Hey,"
    html = build_email_html(
        body_html=(
            f"<p>{salutation}</p>"
            f"<p>I noticed you signed up for PersonnaPress but haven't created your first campaign yet. "
            f"I'm Boris, the founder.</p>"
            f"<p>Getting started is simple: paste a few bullet points about what's on your mind this week, "
            f"and PersonnaPress writes a full blog post in your voice and publishes it wherever you need it.</p>"
            f"<p>If you hit a snag or have questions, just reply to this email. "
            f"It goes straight to my inbox.</p>"
        ),
        cta_text="Create your first campaign",
        cta_url=f"{settings.APP_URL}/dashboard",
    )
    resend.Emails.send({
        "from": settings.EMAIL_FROM,
        "to": [to_email],
        "reply_to": "support@personnapress.com",
        "subject": "Quick check-in from Boris at PersonnaPress",
        "html": html,
    })
