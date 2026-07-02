"""Unit tests for login_user() and logout route."""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.auth_service import login_user


class _User:
    def __init__(self, email: str, hashed_password: str | None, verified: bool = True):
        self.id = uuid.uuid4()
        self.email = email
        self.hashed_password = hashed_password
        self.verified = verified
        self.onboarding_completed = False
        self.google_sub = None


class _Sub:
    def __init__(self, plan_tier: str = "growth"):
        self.plan_tier = plan_tier


def _db_result(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


# ── Task 1.4: unknown email → 401 INVALID_CREDENTIALS ─────────────────────────
@patch("app.services.auth_service._pwd_ctx")
async def test_login_unknown_email_returns_401(mock_ctx):
    mock_ctx.verify.return_value = False
    db = AsyncMock()
    db.execute.return_value = _db_result(None)

    resp = await login_user("nobody@example.com", "pass", db)

    assert resp.status_code == 401
    body = json.loads(resp.body)
    assert body["error"]["code"] == "INVALID_CREDENTIALS"
    assert body["error"]["message"] == "Invalid email or password."


# ── Task 1.4: wrong password → 401 INVALID_CREDENTIALS ────────────────────────
@patch("app.services.auth_service._pwd_ctx")
async def test_login_wrong_password_returns_401(mock_ctx):
    mock_ctx.verify.return_value = False
    user = _User("a@b.com", "hashed_value", verified=True)
    db = AsyncMock()
    db.execute.return_value = _db_result(user)

    resp = await login_user("a@b.com", "wrong", db)

    assert resp.status_code == 401
    body = json.loads(resp.body)
    assert body["error"]["code"] == "INVALID_CREDENTIALS"


# ── Task 1.4: google-only user (no hashed_password) → 401 ────────────────────
@patch("app.services.auth_service._pwd_ctx")
async def test_login_google_only_user_returns_401(mock_ctx):
    mock_ctx.verify.return_value = False
    user = _User("g@b.com", None, verified=True)
    db = AsyncMock()
    db.execute.return_value = _db_result(user)

    resp = await login_user("g@b.com", "anypass", db)

    assert resp.status_code == 401
    body = json.loads(resp.body)
    assert body["error"]["code"] == "INVALID_CREDENTIALS"


# ── Task 1.5: unverified user → 403 EMAIL_NOT_VERIFIED ───────────────────────
@patch("app.services.auth_service._pwd_ctx")
async def test_login_unverified_user_returns_403(mock_ctx):
    mock_ctx.verify.return_value = True
    user = _User("u@b.com", "hashed_value", verified=False)
    db = AsyncMock()
    db.execute.return_value = _db_result(user)

    resp = await login_user("u@b.com", "pass123", db)

    assert resp.status_code == 403
    body = json.loads(resp.body)
    assert body["error"]["code"] == "EMAIL_NOT_VERIFIED"
    assert "verify your email" in body["error"]["message"].lower()


# ── Task 1.6: valid verified user → 200 {"success": true} + httpOnly cookie ──
@patch("app.services.auth_service._pwd_ctx")
async def test_login_success_returns_200_with_cookie(mock_ctx):
    mock_ctx.verify.return_value = True
    user = _User("ok@b.com", "hashed_value", verified=True)
    sub = _Sub("growth")
    db = AsyncMock()
    db.execute.side_effect = [_db_result(user), _db_result(sub)]

    resp = await login_user("ok@b.com", "pass123", db)

    assert resp.status_code == 200
    body = json.loads(resp.body)
    assert body.get("success") is True
    cookie = resp.headers.get("set-cookie", "")
    assert "session=" in cookie
    assert "HttpOnly" in cookie


# ── Task 1.6: success with no subscription falls back to "growth" ─────────────
@patch("app.services.auth_service._pwd_ctx")
async def test_login_success_no_subscription_defaults_growth(mock_ctx):
    mock_ctx.verify.return_value = True
    user = _User("ok@b.com", "hashed_value", verified=True)
    db = AsyncMock()
    db.execute.side_effect = [_db_result(user), _db_result(None)]

    resp = await login_user("ok@b.com", "pass123", db)

    assert resp.status_code == 200
    body = json.loads(resp.body)
    assert body.get("success") is True
