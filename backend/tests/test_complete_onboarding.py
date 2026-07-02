"""Unit tests for complete_onboarding() service function."""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.auth_service import complete_onboarding


class _User:
    def __init__(self):
        self.id = uuid.uuid4()
        self.email = "user@example.com"
        self.verified = True
        self.onboarding_completed = False
        self.google_sub = None
        self.hashed_password = None


class _Sub:
    def __init__(self, plan_tier: str = "growth"):
        self.plan_tier = plan_tier


def _db_result(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


# ── User not found → 404 ──────────────────────────────────────────────────────
async def test_complete_onboarding_user_not_found_raises_404():
    from fastapi import HTTPException

    db = AsyncMock()
    db.execute.return_value = _db_result(None)

    with pytest.raises(HTTPException) as exc_info:
        await complete_onboarding(uuid.uuid4(), db)

    assert exc_info.value.status_code == 404


# ── Valid user → sets onboarding_completed=True and re-issues JWT ─────────────
async def test_complete_onboarding_sets_flag_and_returns_200():
    user = _User()
    sub = _Sub("growth")
    db = AsyncMock()
    db.execute.side_effect = [_db_result(user), _db_result(sub)]
    db.refresh = AsyncMock(side_effect=lambda u: setattr(u, "onboarding_completed", True))

    resp = await complete_onboarding(user.id, db)

    assert resp.status_code == 200
    body = json.loads(resp.body)
    assert body.get("status") == "ok"

    # cookie should be set
    cookie = resp.headers.get("set-cookie", "")
    assert "session=" in cookie
    assert "HttpOnly" in cookie

    # DB commit was called
    db.commit.assert_called_once()


# ── onboarding_completed appears in JWT payload ───────────────────────────────
async def test_complete_onboarding_jwt_contains_flag():
    from jose import jwt as _jwt
    from app.core.config import settings

    user = _User()
    sub = _Sub("growth")
    db = AsyncMock()
    db.execute.side_effect = [_db_result(user), _db_result(sub)]

    async def _refresh(u):
        u.onboarding_completed = True

    db.refresh = AsyncMock(side_effect=_refresh)
    db.commit = AsyncMock()

    resp = await complete_onboarding(user.id, db)

    cookie_header = resp.headers.get("set-cookie", "")
    # Extract token value from cookie: "session=<token>; ..."
    token = cookie_header.split("session=")[1].split(";")[0]
    payload = _jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    assert payload["onboarding_completed"] is True
