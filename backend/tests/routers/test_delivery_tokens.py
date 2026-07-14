"""Tests for delivery token management endpoints on /clients/{id}/delivery-tokens."""
import sys
import types as _types
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Stub slowapi (needed because test_public_articles imports it first in some orderings,
# but we need it here too when this file is run alone)
for _mod_name in ("slowapi", "slowapi.errors", "slowapi.middleware", "slowapi.util"):
    if _mod_name not in sys.modules:
        _stub = _types.ModuleType(_mod_name)
        sys.modules[_mod_name] = _stub

if not hasattr(sys.modules["slowapi"], "Limiter"):
    def _noop_limiter(*a, **kw):
        m = MagicMock()
        m.limit = lambda *a, **kw: (lambda fn: fn)
        return m
    sys.modules["slowapi"].Limiter = _noop_limiter
if not hasattr(sys.modules["slowapi.errors"], "RateLimitExceeded"):
    sys.modules["slowapi.errors"].RateLimitExceeded = type("RateLimitExceeded", (Exception,), {})
if not hasattr(sys.modules["slowapi.middleware"], "SlowAPIMiddleware"):
    sys.modules["slowapi.middleware"].SlowAPIMiddleware = MagicMock()
if not hasattr(sys.modules["slowapi.util"], "get_remote_address"):
    sys.modules["slowapi.util"].get_remote_address = MagicMock(return_value="127.0.0.1")


def _utc() -> datetime:
    return datetime(2026, 1, 1, tzinfo=timezone.utc).replace(tzinfo=None)


def _make_client(user_id=None, client_id=None):
    c = MagicMock()
    c.id = client_id or uuid.uuid4()
    c.user_id = user_id or uuid.uuid4()
    return c


def _make_token_record(client_id=None, revoked=False):
    t = MagicMock()
    t.id = uuid.uuid4()
    t.client_id = client_id or uuid.uuid4()
    t.name = "My Token"
    t.token_prefix = "ppd_abc1"
    t.token_hash = "fakehash"
    t.revoked_at = _utc() if revoked else None
    t.last_used_at = None
    t.created_at = _utc()
    return t


# ---------------------------------------------------------------------------
# POST /clients/{id}/delivery-tokens — create token
# ---------------------------------------------------------------------------

async def test_create_token_returns_raw_token_once():
    from app.routers.clients import create_client_delivery_token
    from app.schemas.client import DeliveryTokenCreate

    user_id = uuid.uuid4()
    client_id = uuid.uuid4()
    client = _make_client(user_id=user_id, client_id=client_id)
    token_record = _make_token_record(client_id=client_id)
    raw = "ppd_rawsecretvalue12345678901234567890"

    db = AsyncMock()
    db.commit = AsyncMock()

    with patch("app.routers.clients.get_client", new=AsyncMock(return_value=client)):
        with patch("app.routers.clients.create_delivery_token", new=AsyncMock(return_value=(token_record, raw))):
            result = await create_client_delivery_token(
                client_id=client_id,
                body=DeliveryTokenCreate(name="My Token"),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert result.token == raw
    assert result.id == token_record.id
    assert result.name == "My Token"


async def test_create_token_wrong_user_404():
    from app.routers.clients import create_client_delivery_token
    from app.schemas.client import DeliveryTokenCreate
    from fastapi import HTTPException

    user_id = uuid.uuid4()
    other_user = uuid.uuid4()
    client_id = uuid.uuid4()
    client = _make_client(user_id=other_user, client_id=client_id)

    db = AsyncMock()

    with patch("app.routers.clients.get_client", new=AsyncMock(return_value=client)):
        with pytest.raises(HTTPException) as exc:
            await create_client_delivery_token(
                client_id=client_id,
                body=DeliveryTokenCreate(name="Token"),
                current_user={"user_id": str(user_id)},
                db=db,
            )
    assert exc.value.status_code == 404


async def test_create_token_client_not_found_404():
    from app.routers.clients import create_client_delivery_token
    from app.schemas.client import DeliveryTokenCreate
    from fastapi import HTTPException

    user_id = uuid.uuid4()
    db = AsyncMock()

    with patch("app.routers.clients.get_client", new=AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as exc:
            await create_client_delivery_token(
                client_id=uuid.uuid4(),
                body=DeliveryTokenCreate(name="Token"),
                current_user={"user_id": str(user_id)},
                db=db,
            )
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# GET /clients/{id}/delivery-tokens — list tokens
# ---------------------------------------------------------------------------

async def test_list_tokens_omits_secrets():
    from app.routers.clients import list_client_delivery_tokens

    user_id = uuid.uuid4()
    client_id = uuid.uuid4()
    client = _make_client(user_id=user_id, client_id=client_id)
    token_record = _make_token_record(client_id=client_id)

    db = AsyncMock()

    with patch("app.routers.clients.get_client", new=AsyncMock(return_value=client)):
        with patch("app.routers.clients.list_delivery_tokens", new=AsyncMock(return_value=[token_record])):
            result = await list_client_delivery_tokens(
                client_id=client_id,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert len(result.items) == 1
    item = result.items[0]
    # Must NOT expose token or token_hash
    assert not hasattr(item, "token")
    assert not hasattr(item, "token_hash")
    assert item.token_prefix == "ppd_abc1"


async def test_list_tokens_shows_revoked_state():
    from app.routers.clients import list_client_delivery_tokens

    user_id = uuid.uuid4()
    client_id = uuid.uuid4()
    client = _make_client(user_id=user_id, client_id=client_id)
    active = _make_token_record(client_id=client_id, revoked=False)
    revoked = _make_token_record(client_id=client_id, revoked=True)

    db = AsyncMock()

    with patch("app.routers.clients.get_client", new=AsyncMock(return_value=client)):
        with patch("app.routers.clients.list_delivery_tokens", new=AsyncMock(return_value=[active, revoked])):
            result = await list_client_delivery_tokens(
                client_id=client_id,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert result.items[0].revoked is False
    assert result.items[1].revoked is True


# ---------------------------------------------------------------------------
# DELETE /clients/{id}/delivery-tokens/{token_id} — revoke
# ---------------------------------------------------------------------------

async def test_revoke_token_returns_204():
    from app.routers.clients import revoke_client_delivery_token

    user_id = uuid.uuid4()
    client_id = uuid.uuid4()
    token_id = uuid.uuid4()
    client = _make_client(user_id=user_id, client_id=client_id)
    token = _make_token_record(client_id=client_id)
    token.id = token_id

    db = AsyncMock()
    db.commit = AsyncMock()

    with patch("app.routers.clients.get_client", new=AsyncMock(return_value=client)):
        with patch("app.routers.clients.get_delivery_token", new=AsyncMock(return_value=token)):
            with patch("app.routers.clients.revoke_delivery_token", new=AsyncMock(return_value=token)):
                resp = await revoke_client_delivery_token(
                    client_id=client_id,
                    token_id=token_id,
                    current_user={"user_id": str(user_id)},
                    db=db,
                )

    assert resp.status_code == 204


async def test_revoke_token_wrong_client_404():
    from app.routers.clients import revoke_client_delivery_token
    from fastapi import HTTPException

    user_id = uuid.uuid4()
    client_id = uuid.uuid4()
    other_client = uuid.uuid4()
    token_id = uuid.uuid4()
    client = _make_client(user_id=user_id, client_id=client_id)
    # token belongs to a different client
    token = _make_token_record(client_id=other_client)
    token.id = token_id

    db = AsyncMock()

    with patch("app.routers.clients.get_client", new=AsyncMock(return_value=client)):
        with patch("app.routers.clients.get_delivery_token", new=AsyncMock(return_value=token)):
            with pytest.raises(HTTPException) as exc:
                await revoke_client_delivery_token(
                    client_id=client_id,
                    token_id=token_id,
                    current_user={"user_id": str(user_id)},
                    db=db,
                )
    assert exc.value.status_code == 404


async def test_revoke_nonexistent_token_404():
    from app.routers.clients import revoke_client_delivery_token
    from fastapi import HTTPException

    user_id = uuid.uuid4()
    client_id = uuid.uuid4()
    client = _make_client(user_id=user_id, client_id=client_id)

    db = AsyncMock()

    with patch("app.routers.clients.get_client", new=AsyncMock(return_value=client)):
        with patch("app.routers.clients.get_delivery_token", new=AsyncMock(return_value=None)):
            with pytest.raises(HTTPException) as exc:
                await revoke_client_delivery_token(
                    client_id=client_id,
                    token_id=uuid.uuid4(),
                    current_user={"user_id": str(user_id)},
                    db=db,
                )
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# CORS check (structural)
# ---------------------------------------------------------------------------

def test_public_app_cors_allows_all_origins():
    """Verify the public sub-app has wildcard CORS, main app does not."""
    from app.routers.public_articles import public_app

    # Find CORSMiddleware kwargs from user_middleware (registered before stack build)
    public_origins = None
    for mw in public_app.user_middleware:
        cls = getattr(mw, "cls", None)
        if cls is not None and getattr(cls, "__name__", "") == "CORSMiddleware":
            public_origins = mw.kwargs.get("allow_origins")
            break

    assert public_origins == ["*"], f"Expected ['*'] for public_app CORS, got {public_origins}"


def test_main_app_cors_is_not_wildcard():
    """Main app CORS setting (in main.py) must list a specific origin, not wildcard.
    We verify by reading the source rather than importing main (too many deps to stub)."""
    import ast, pathlib
    src = pathlib.Path("app/main.py").read_text()
    # The main app CORS must NOT have allow_origins=["*"]
    # It uses settings.APP_URL — confirm '*' is not in the wildcard position
    assert 'allow_origins=["*"]' not in src, "Main app must not use wildcard CORS"
    assert "allow_origins=[settings.APP_URL]" in src, "Main app must use settings.APP_URL for CORS"
