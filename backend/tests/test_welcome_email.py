"""Tests for send_welcome_email and its fire-and-forget hooks in auth_service."""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.email import send_welcome_email
from app.services.auth_service import auth_google, verify_email_token


# ── Helpers ──────────────────────────────────────────────────────────────────

class _User:
    def __init__(self, email: str, verified: bool = False):
        self.id = uuid.uuid4()
        self.email = email
        self.verified = verified
        self.hashed_password = None
        self.google_sub = None
        self.onboarding_completed = False


class _Sub:
    def __init__(self, plan_tier: str = "growth"):
        self.plan_tier = plan_tier


def _db_result(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


# ── send_welcome_email unit tests ─────────────────────────────────────────────

@patch("app.integrations.email.resend.Emails.send")
def test_welcome_email_subject_and_reply_to(mock_send):
    send_welcome_email("user@example.com", None)

    mock_send.assert_called_once()
    payload = mock_send.call_args[0][0]
    assert payload["subject"] == "You're in - here's what to do first"
    assert payload["reply_to"] == "support@personnapress.com"
    assert payload["to"] == ["user@example.com"]


@patch("app.integrations.email.resend.Emails.send")
def test_welcome_email_cta_in_html(mock_send):
    send_welcome_email("user@example.com", None)

    html = mock_send.call_args[0][0]["html"]
    assert "Create your first client" in html
    assert "/dashboard" in html


@patch("app.integrations.email.resend.Emails.send")
def test_welcome_email_salutation_with_first_name(mock_send):
    send_welcome_email("user@example.com", "Alice")

    html = mock_send.call_args[0][0]["html"]
    assert "Hey Alice," in html


@patch("app.integrations.email.resend.Emails.send")
def test_welcome_email_salutation_without_first_name(mock_send):
    send_welcome_email("user@example.com", None)

    html = mock_send.call_args[0][0]["html"]
    assert "Hey," in html
    assert "Hey None," not in html


@patch("app.integrations.email.resend.Emails.send")
def test_welcome_email_no_em_dash(mock_send):
    send_welcome_email("user@example.com", "Boris")

    payload = mock_send.call_args[0][0]
    combined = payload["subject"] + payload["html"]
    assert "—" not in combined  # em-dash


# ── verify_email_token hook tests ─────────────────────────────────────────────

@patch("app.services.auth_service._schedule_welcome_email")
@patch("app.services.auth_service._schedule_add_contact")
@patch("app.services.auth_service._issue_session", new_callable=AsyncMock)
async def test_verify_email_fires_welcome_for_unverified_user(
    mock_issue, mock_add_contact, mock_welcome
):
    user = _User("a@b.com", verified=False)
    db = AsyncMock()
    db.execute.return_value = _db_result(user)

    with patch("app.services.auth_service.decode_verification_token", return_value="a@b.com"):
        await verify_email_token("valid-token", db)

    mock_welcome.assert_called_once_with("a@b.com")


@patch("app.services.auth_service._schedule_welcome_email")
@patch("app.services.auth_service._schedule_add_contact")
@patch("app.services.auth_service._issue_session", new_callable=AsyncMock)
async def test_verify_email_no_welcome_for_already_verified_user(
    mock_issue, mock_add_contact, mock_welcome
):
    user = _User("a@b.com", verified=True)
    db = AsyncMock()
    db.execute.return_value = _db_result(user)

    with patch("app.services.auth_service.decode_verification_token", return_value="a@b.com"):
        await verify_email_token("valid-token", db)

    mock_welcome.assert_not_called()


# ── auth_google hook tests ────────────────────────────────────────────────────

@patch("app.services.auth_service._schedule_welcome_email")
@patch("app.services.auth_service._schedule_add_contact")
@patch("app.services.auth_service._issue_session", new_callable=AsyncMock)
@patch("app.services.auth_service._new_subscription", new_callable=AsyncMock)
async def test_auth_google_fires_welcome_for_new_user(
    mock_sub, mock_issue, mock_add_contact, mock_welcome
):
    db = AsyncMock()
    # Both lookups (by google_sub, then by email) return None → brand-new user
    db.execute.return_value = _db_result(None)

    await auth_google("google-sub-123", "new@example.com", True, db)

    mock_welcome.assert_called_once_with("new@example.com")


@patch("app.services.auth_service._schedule_welcome_email")
@patch("app.services.auth_service._schedule_add_contact")
@patch("app.services.auth_service._issue_session", new_callable=AsyncMock)
async def test_auth_google_no_welcome_for_returning_user(
    mock_issue, mock_add_contact, mock_welcome
):
    existing_user = _User("existing@example.com", verified=True)
    existing_user.google_sub = "google-sub-456"
    sub = _Sub()

    db = AsyncMock()
    # First call returns the existing user (by google_sub), second call returns sub
    db.execute.side_effect = [_db_result(existing_user), _db_result(sub)]

    await auth_google("google-sub-456", "existing@example.com", True, db)

    mock_welcome.assert_not_called()
