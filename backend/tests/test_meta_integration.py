"""Tests for Meta OAuth callback endpoint and meta.py integration helpers."""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx
from fastapi import HTTPException


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_client(user_id=None, client_id=None):
    c = MagicMock()
    c.id = client_id or uuid.uuid4()
    c.user_id = user_id or uuid.uuid4()
    return c


def _make_httpx_response(status_code: int, json_data: dict) -> httpx.Response:
    """Create a mock httpx Response."""
    return httpx.Response(
        status_code=status_code,
        content=json.dumps(json_data).encode(),
        headers={"content-type": "application/json"},
    )


# ── meta.py: token exchange ───────────────────────────────────────────────────

async def test_meta_token_exchange_success():
    """Short-lived and long-lived token exchange calls are made in correct order."""
    from app.integrations.meta import (
        exchange_code_for_short_lived_token,
        exchange_short_lived_for_long_lived_token,
    )

    short_token_resp = _make_httpx_response(200, {"access_token": "short_token_abc"})
    long_token_resp = _make_httpx_response(200, {"access_token": "long_token_xyz"})

    with patch("httpx.AsyncClient") as mock_client_cls:
        # exchange_code_for_short_lived_token uses POST
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=short_token_resp)
        mock_client_cls.return_value = mock_client

        short_token = await exchange_code_for_short_lived_token("auth_code_123", "https://example.com/api/auth/meta/callback")

    assert short_token == "short_token_abc"

    with patch("httpx.AsyncClient") as mock_client_cls:
        # exchange_short_lived_for_long_lived_token uses GET
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=long_token_resp)
        mock_client_cls.return_value = mock_client

        long_token = await exchange_short_lived_for_long_lived_token("short_token_abc")

    assert long_token == "long_token_xyz"


async def test_meta_token_exchange_error_raises():
    """Token exchange failure raises PlatformError."""
    from app.integrations.meta import exchange_code_for_short_lived_token
    from app.core.exceptions import PlatformError

    error_resp = _make_httpx_response(400, {"error": {"message": "Invalid OAuth code"}})

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=error_resp)
        mock_client_cls.return_value = mock_client

        with pytest.raises(PlatformError) as exc_info:
            await exchange_code_for_short_lived_token("bad_code", "https://example.com/api/auth/meta/callback")

    assert exc_info.value.status_code == 400
    assert "Invalid OAuth code" in str(exc_info.value.message)


# ── meta.py: discover_accounts ────────────────────────────────────────────────

async def test_meta_discover_accounts_instagram_and_facebook():
    """discover_accounts with instagram_business_account returns page data correctly."""
    from app.integrations.meta import discover_accounts

    pages_resp = _make_httpx_response(200, {
        "data": [
            {
                "id": "page_111",
                "name": "My Brand Page",
                "access_token": "page_access_token_aaa",
                "instagram_business_account": {
                    "id": "ig_222",
                    "username": "mybrand",
                },
            }
        ]
    })

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=pages_resp)
        mock_client_cls.return_value = mock_client

        pages = await discover_accounts("long_lived_user_token")

    assert len(pages) == 1
    page = pages[0]
    assert page["id"] == "page_111"
    assert page["instagram_business_account"]["id"] == "ig_222"
    assert page["instagram_business_account"]["username"] == "mybrand"


async def test_meta_discover_accounts_no_instagram():
    """discover_accounts page without instagram_business_account field is returned as-is."""
    from app.integrations.meta import discover_accounts

    pages_resp = _make_httpx_response(200, {
        "data": [
            {
                "id": "page_333",
                "name": "Another Page",
                "access_token": "page_access_token_bbb",
                # no instagram_business_account key
            }
        ]
    })

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=pages_resp)
        mock_client_cls.return_value = mock_client

        pages = await discover_accounts("long_lived_user_token")

    assert len(pages) == 1
    assert "instagram_business_account" not in pages[0]


# ── meta.py: discover_threads_user_id ─────────────────────────────────────────

async def test_meta_threads_discovery_present():
    """discover_threads_user_id returns threads_user_id when present."""
    from app.integrations.meta import discover_threads_user_id

    threads_resp = _make_httpx_response(200, {
        "id": "ig_222",
        "threads_user_id": "threads_444",
    })

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=threads_resp)
        mock_client_cls.return_value = mock_client

        result = await discover_threads_user_id("ig_222", "long_lived_user_token")

    assert result == "threads_444"


async def test_meta_threads_discovery_absent():
    """discover_threads_user_id returns None when threads_user_id missing, no exception."""
    from app.integrations.meta import discover_threads_user_id

    no_threads_resp = _make_httpx_response(200, {
        "id": "ig_222",
        # threads_user_id absent
    })

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=no_threads_resp)
        mock_client_cls.return_value = mock_client

        result = await discover_threads_user_id("ig_222", "long_lived_user_token")

    assert result is None


async def test_meta_threads_discovery_non_200_no_exception():
    """discover_threads_user_id returns None on non-200 response without raising."""
    from app.integrations.meta import discover_threads_user_id

    error_resp = _make_httpx_response(400, {"error": {"message": "Threads not connected"}})

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=error_resp)
        mock_client_cls.return_value = mock_client

        result = await discover_threads_user_id("ig_222", "long_lived_user_token")

    assert result is None


# ── publishing.py: meta_oauth_callback ────────────────────────────────────────

async def test_meta_callback_upserts_instagram_and_facebook():
    """meta_oauth_callback upserts instagram and facebook_page when page has instagram account."""
    from app.routers.publishing import meta_oauth_callback, OAuthCallbackRequest

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    pages_data = [
        {
            "id": "page_111",
            "name": "My Brand Page",
            "access_token": "page_access_token_aaa",
            "instagram_business_account": {
                "id": "ig_222",
                "username": "mybrand",
            },
        }
    ]

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.meta_integration.exchange_code_for_short_lived_token",
              AsyncMock(return_value="short_token")),
        patch("app.routers.publishing.meta_integration.exchange_short_lived_for_long_lived_token",
              AsyncMock(return_value="long_token")),
        patch("app.routers.publishing.meta_integration.discover_accounts",
              AsyncMock(return_value=pages_data)),
        patch("app.routers.publishing.meta_integration.discover_threads_user_id",
              AsyncMock(return_value=None)),
        patch("app.routers.publishing.upsert_connection", AsyncMock()) as mock_upsert,
    ):
        result = await meta_oauth_callback(
            client_id=client.id,
            body=OAuthCallbackRequest(code="auth_code"),
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert "connected_platforms" in result
    assert "instagram" in result["connected_platforms"]
    assert "facebook_page" in result["connected_platforms"]
    assert "threads" not in result["connected_platforms"]

    upsert_calls = mock_upsert.call_args_list
    platforms_upserted = [call.args[2] for call in upsert_calls]
    assert "instagram" in platforms_upserted
    assert "facebook_page" in platforms_upserted


async def test_meta_callback_no_instagram_only_facebook():
    """meta_oauth_callback upserts only facebook_page when no instagram_business_account."""
    from app.routers.publishing import meta_oauth_callback, OAuthCallbackRequest

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    pages_data = [
        {
            "id": "page_333",
            "name": "Another Page",
            "access_token": "page_token_bbb",
            # no instagram_business_account
        }
    ]

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.meta_integration.exchange_code_for_short_lived_token",
              AsyncMock(return_value="short_token")),
        patch("app.routers.publishing.meta_integration.exchange_short_lived_for_long_lived_token",
              AsyncMock(return_value="long_token")),
        patch("app.routers.publishing.meta_integration.discover_accounts",
              AsyncMock(return_value=pages_data)),
        patch("app.routers.publishing.meta_integration.discover_threads_user_id",
              AsyncMock(return_value=None)),
        patch("app.routers.publishing.upsert_connection", AsyncMock()) as mock_upsert,
    ):
        result = await meta_oauth_callback(
            client_id=client.id,
            body=OAuthCallbackRequest(code="auth_code"),
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert "instagram" not in result["connected_platforms"]
    assert "facebook_page" in result["connected_platforms"]

    upsert_calls = mock_upsert.call_args_list
    platforms_upserted = [call.args[2] for call in upsert_calls]
    assert "instagram" not in platforms_upserted
    assert "facebook_page" in platforms_upserted


async def test_meta_threads_discovery_present_upserted():
    """meta_oauth_callback upserts threads when threads_user_id is found."""
    from app.routers.publishing import meta_oauth_callback, OAuthCallbackRequest

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    pages_data = [
        {
            "id": "page_111",
            "name": "My Brand",
            "access_token": "page_token_aaa",
            "instagram_business_account": {"id": "ig_222", "username": "mybrand"},
        }
    ]

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.meta_integration.exchange_code_for_short_lived_token",
              AsyncMock(return_value="short_token")),
        patch("app.routers.publishing.meta_integration.exchange_short_lived_for_long_lived_token",
              AsyncMock(return_value="long_token")),
        patch("app.routers.publishing.meta_integration.discover_accounts",
              AsyncMock(return_value=pages_data)),
        patch("app.routers.publishing.meta_integration.discover_threads_user_id",
              AsyncMock(return_value="threads_444")),
        patch("app.routers.publishing.upsert_connection", AsyncMock()) as mock_upsert,
    ):
        result = await meta_oauth_callback(
            client_id=client.id,
            body=OAuthCallbackRequest(code="auth_code"),
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert "threads" in result["connected_platforms"]
    platforms_upserted = [call.args[2] for call in mock_upsert.call_args_list]
    assert "threads" in platforms_upserted


async def test_meta_callback_csrf_ownership_wrong_user():
    """meta_oauth_callback raises 404 when called by a different user (ownership check)."""
    from app.routers.publishing import meta_oauth_callback, OAuthCallbackRequest

    owner_id = uuid.uuid4()
    attacker_id = uuid.uuid4()
    client = _make_client(user_id=owner_id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await meta_oauth_callback(
                client_id=client.id,
                body=OAuthCallbackRequest(code="auth_code"),
                current_user={"user_id": str(attacker_id)},
                db=db,
            )

    assert exc_info.value.status_code == 404


async def test_meta_callback_token_exchange_failure_raises_400():
    """meta_oauth_callback raises 400 when short-lived token exchange fails."""
    from app.routers.publishing import meta_oauth_callback, OAuthCallbackRequest
    from app.core.exceptions import PlatformError

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.meta_integration.exchange_code_for_short_lived_token",
              AsyncMock(side_effect=PlatformError("Meta", 400, "Invalid code"))),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await meta_oauth_callback(
                client_id=client.id,
                body=OAuthCallbackRequest(code="bad_code"),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400


# ── meta.py: additional error coverage ───────────────────────────────────────

async def test_meta_long_lived_token_exchange_error_raises():
    """exchange_short_lived_for_long_lived_token failure raises PlatformError."""
    from app.integrations.meta import exchange_short_lived_for_long_lived_token
    from app.core.exceptions import PlatformError

    error_resp = _make_httpx_response(400, {"error": {"message": "Token has expired"}})

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=error_resp)
        mock_client_cls.return_value = mock_client

        with pytest.raises(PlatformError) as exc_info:
            await exchange_short_lived_for_long_lived_token("expired_short_token")

    assert exc_info.value.status_code == 400
    assert "Token has expired" in str(exc_info.value.message)


async def test_meta_discover_accounts_error_raises():
    """discover_accounts raises PlatformError on non-200 response."""
    from app.integrations.meta import discover_accounts
    from app.core.exceptions import PlatformError

    error_resp = _make_httpx_response(401, {"error": {"message": "Invalid OAuth access token"}})

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=error_resp)
        mock_client_cls.return_value = mock_client

        with pytest.raises(PlatformError) as exc_info:
            await discover_accounts("invalid_token")

    assert exc_info.value.status_code == 401


async def test_meta_threads_discovery_network_exception_returns_none():
    """discover_threads_user_id returns None (not raises) when network throws."""
    from app.integrations.meta import discover_threads_user_id

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused", request=None))
        mock_client_cls.return_value = mock_client

        result = await discover_threads_user_id("ig_222", "some_token")

    assert result is None


# ── publishing.py: meta_oauth_callback edge cases ─────────────────────────────

async def test_meta_callback_empty_pages_raises_422():
    """meta_oauth_callback with no pages raises 422 NO_ACCOUNTS_FOUND."""
    from app.routers.publishing import meta_oauth_callback, OAuthCallbackRequest

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.meta_integration.exchange_code_for_short_lived_token",
              AsyncMock(return_value="short_token")),
        patch("app.routers.publishing.meta_integration.exchange_short_lived_for_long_lived_token",
              AsyncMock(return_value="long_token")),
        patch("app.routers.publishing.meta_integration.discover_accounts",
              AsyncMock(return_value=[])),
        patch("app.routers.publishing.meta_integration.discover_threads_user_id",
              AsyncMock(return_value=None)),
        patch("app.routers.publishing.upsert_connection", AsyncMock()) as mock_upsert,
    ):
        with pytest.raises(HTTPException) as exc_info:
            await meta_oauth_callback(
                client_id=client.id,
                body=OAuthCallbackRequest(code="auth_code"),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["error"]["code"] == "NO_ACCOUNTS_FOUND"
    mock_upsert.assert_not_called()


async def test_meta_callback_multiple_pages_threads_discovery_uses_first_instagram():
    """meta_oauth_callback with multiple pages calls Threads discovery with first instagram user ID."""
    from app.routers.publishing import meta_oauth_callback, OAuthCallbackRequest

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    pages_data = [
        {
            "id": "page_111",
            "name": "Brand Page 1",
            "access_token": "page_token_aaa",
            "instagram_business_account": {"id": "ig_222", "username": "brand1"},
        },
        {
            "id": "page_333",
            "name": "Brand Page 2",
            "access_token": "page_token_bbb",
            "instagram_business_account": {"id": "ig_444", "username": "brand2"},
        },
    ]

    threads_discovery_mock = AsyncMock(return_value="threads_555")

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.meta_integration.exchange_code_for_short_lived_token",
              AsyncMock(return_value="short_token")),
        patch("app.routers.publishing.meta_integration.exchange_short_lived_for_long_lived_token",
              AsyncMock(return_value="long_token")),
        patch("app.routers.publishing.meta_integration.discover_accounts",
              AsyncMock(return_value=pages_data)),
        patch("app.routers.publishing.meta_integration.discover_threads_user_id",
              threads_discovery_mock),
        patch("app.routers.publishing.upsert_connection", AsyncMock()),
    ):
        result = await meta_oauth_callback(
            client_id=client.id,
            body=OAuthCallbackRequest(code="auth_code"),
            current_user={"user_id": str(user_id)},
            db=db,
        )

    # Threads discovery must be called only with the FIRST instagram user's ID
    threads_discovery_mock.assert_called_once_with("ig_222", "long_token")
    assert "threads" in result["connected_platforms"]


# ── _extract_identifier: Meta platforms ──────────────────────────────────────

def test_extract_identifier_instagram():
    """_extract_identifier returns username for instagram platform."""
    from app.routers.publishing import _extract_identifier
    from app.core.security import encrypt_credential

    creds = json.dumps({"instagram_user_id": "123", "username": "mybrand", "page_access_token": "tok"})
    assert _extract_identifier("instagram", encrypt_credential(creds)) == "mybrand"


def test_extract_identifier_facebook_page():
    """_extract_identifier returns page_name for facebook_page platform."""
    from app.routers.publishing import _extract_identifier
    from app.core.security import encrypt_credential

    creds = json.dumps({"page_id": "111", "page_name": "My Brand Page", "page_access_token": "tok"})
    assert _extract_identifier("facebook_page", encrypt_credential(creds)) == "My Brand Page"


def test_extract_identifier_threads():
    """_extract_identifier returns username for threads platform."""
    from app.routers.publishing import _extract_identifier
    from app.core.security import encrypt_credential

    creds = json.dumps({"threads_user_id": "444", "username": "mybrand", "user_access_token": "tok"})
    assert _extract_identifier("threads", encrypt_credential(creds)) == "mybrand"
