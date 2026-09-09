"""Unit tests for Story 26.5 -- onboarding step persistence and voice preview.

Covers:
- PATCH /auth/onboarding-step: validates input, persists step, returns ok
- complete_onboarding clears onboarding_step (sets to None)
- voice-preview: happy path, timeout (502), no BVP (404), ownership (404)
"""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch, AsyncMock as _AsyncMock

import pytest

from app.services.auth_service import complete_onboarding, patch_onboarding_step


# ── Helpers ───────────────────────────────────────────────────────────────────

class _User:
    def __init__(self):
        self.id = uuid.uuid4()
        self.email = "user@example.com"
        self.verified = True
        self.onboarding_completed = False
        self.onboarding_step = None
        self.google_sub = None
        self.hashed_password = None


class _Sub:
    def __init__(self, plan_tier: str = "growth"):
        self.plan_tier = plan_tier


def _db_result(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


# ── patch_onboarding_step ─────────────────────────────────────────────────────

async def test_patch_onboarding_step_persists_step():
    user = _User()
    sub = _Sub()
    db = AsyncMock()
    db.execute.side_effect = [_db_result(user), _db_result(sub)]

    resp = await patch_onboarding_step(user.id, 2, db)

    assert resp.status_code == 200
    body = json.loads(resp.body)
    assert body["status"] == "ok"
    assert body["onboarding_step"] == 2
    assert user.onboarding_step == 2
    db.commit.assert_called_once()


async def test_patch_onboarding_step_user_not_found_raises_404():
    from fastapi import HTTPException

    db = AsyncMock()
    db.execute.return_value = _db_result(None)

    with pytest.raises(HTTPException) as exc_info:
        await patch_onboarding_step(uuid.uuid4(), 1, db)

    assert exc_info.value.status_code == 404


async def test_patch_onboarding_step_all_valid_steps():
    """Each step value 1-4 should be accepted without error."""
    for step_val in [1, 2, 3, 4]:
        user = _User()
        sub = _Sub()
        db = AsyncMock()
        db.execute.side_effect = [_db_result(user), _db_result(sub)]

        resp = await patch_onboarding_step(user.id, step_val, db)
        assert resp.status_code == 200
        assert user.onboarding_step == step_val


# ── complete_onboarding clears onboarding_step ────────────────────────────────

async def test_complete_onboarding_clears_onboarding_step():
    user = _User()
    user.onboarding_step = 3  # simulating a user who was mid-flow

    sub = _Sub()
    db = AsyncMock()
    db.execute.side_effect = [_db_result(user), _db_result(sub)]

    resp = await complete_onboarding(user.id, db)

    assert resp.status_code == 200
    assert user.onboarding_completed is True
    assert user.onboarding_step is None  # must be cleared
    db.commit.assert_called_once()


# ── Voice preview endpoint ────────────────────────────────────────────────────

class _Client:
    def __init__(self, user_id, brand_voice_profile=None):
        self.id = uuid.uuid4()
        self.user_id = user_id
        self.brand_voice_profile = brand_voice_profile


async def test_voice_preview_happy_path():
    """Voice preview returns the LLM-generated paragraph."""
    from app.routers.clients import get_voice_preview

    user_id = uuid.uuid4()
    bvp = {"voice_brief": "casual, punchy, first-person", "tone": ["casual"]}
    client = _Client(user_id, brand_voice_profile=bvp)

    current_user = {"user_id": str(user_id)}
    db = AsyncMock()

    with patch("app.routers.clients.get_client", return_value=client), \
         patch("app.routers.clients._call_llm_preview", new=AsyncMock(return_value="This is a test preview paragraph.")):
        resp = await get_voice_preview(client.id, current_user, db)

    assert resp.preview == "This is a test preview paragraph."


async def test_voice_preview_no_bvp_returns_404():
    """Client without BVP returns 404."""
    from fastapi import HTTPException
    from app.routers.clients import get_voice_preview

    user_id = uuid.uuid4()
    client = _Client(user_id, brand_voice_profile=None)

    current_user = {"user_id": str(user_id)}
    db = AsyncMock()

    with patch("app.routers.clients.get_client", return_value=client):
        with pytest.raises(HTTPException) as exc_info:
            await get_voice_preview(client.id, current_user, db)

    assert exc_info.value.status_code == 404
    detail = exc_info.value.detail
    assert detail["error"]["code"] == "NO_BVP"


async def test_voice_preview_wrong_owner_returns_404():
    """Client owned by different user returns 404."""
    from fastapi import HTTPException
    from app.routers.clients import get_voice_preview

    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    client = _Client(other_user_id, brand_voice_profile={"voice_brief": "test"})

    current_user = {"user_id": str(user_id)}
    db = AsyncMock()

    with patch("app.routers.clients.get_client", return_value=client):
        with pytest.raises(HTTPException) as exc_info:
            await get_voice_preview(client.id, current_user, db)

    assert exc_info.value.status_code == 404


async def test_voice_preview_provider_timeout_returns_502():
    """Provider timeout results in 502."""
    import asyncio
    from fastapi import HTTPException
    from app.routers.clients import get_voice_preview

    user_id = uuid.uuid4()
    bvp = {"voice_brief": "test", "tone": ["direct"]}
    client = _Client(user_id, brand_voice_profile=bvp)

    current_user = {"user_id": str(user_id)}
    db = AsyncMock()

    async def _timeout(*args, **kwargs):
        raise asyncio.TimeoutError()

    with patch("app.routers.clients.get_client", return_value=client), \
         patch("app.routers.clients._call_llm_preview", new=AsyncMock(side_effect=asyncio.TimeoutError())):
        with pytest.raises(HTTPException) as exc_info:
            await get_voice_preview(client.id, current_user, db)

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail["error"]["code"] == "PROVIDER_ERROR"


async def test_voice_preview_client_not_found_returns_404():
    """Non-existent client returns 404."""
    from fastapi import HTTPException
    from app.routers.clients import get_voice_preview

    user_id = uuid.uuid4()
    current_user = {"user_id": str(user_id)}
    db = AsyncMock()

    with patch("app.routers.clients.get_client", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await get_voice_preview(uuid.uuid4(), current_user, db)

    assert exc_info.value.status_code == 404


async def test_voice_preview_legacy_bvp_uses_default_voice():
    """Legacy BVP without voice_brief falls back to _DEFAULT_VOICE passed to LLM."""
    from app.routers.clients import get_voice_preview
    from app.integrations.generation_prompts import _DEFAULT_VOICE

    user_id = uuid.uuid4()
    # Legacy BVP: no voice_brief field
    legacy_bvp = {"tone": ["professional"], "cadence": {}, "banned_jargon": []}
    client = _Client(user_id, brand_voice_profile=legacy_bvp)

    current_user = {"user_id": str(user_id)}
    db = AsyncMock()

    captured_args: list = []

    async def capture_call(voice_section: str) -> str:
        captured_args.append(voice_section)
        return "A professional preview sentence for legacy voice."

    with patch("app.routers.clients.get_client", return_value=client), \
         patch("app.routers.clients._call_llm_preview", new=capture_call):
        resp = await get_voice_preview(client.id, current_user, db)

    assert resp.preview == "A professional preview sentence for legacy voice."
    assert len(captured_args) == 1
    assert captured_args[0] == _DEFAULT_VOICE
