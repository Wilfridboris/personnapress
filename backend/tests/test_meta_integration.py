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
    """meta_oauth_callback no longer upserts threads -- Threads has its own OAuth flow."""
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
        patch("app.routers.publishing.upsert_connection", AsyncMock()) as mock_upsert,
    ):
        result = await meta_oauth_callback(
            client_id=client.id,
            body=OAuthCallbackRequest(code="auth_code"),
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert "threads" not in result["connected_platforms"]
    assert "instagram" in result["connected_platforms"]
    assert "facebook_page" in result["connected_platforms"]
    platforms_upserted = [call.args[2] for call in mock_upsert.call_args_list]
    assert "threads" not in platforms_upserted


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


async def test_meta_callback_single_page_unchanged():
    """meta_oauth_callback with 1 page: upsert called, returns dict with connected_platforms (HTTP 201)."""
    from app.routers.publishing import meta_oauth_callback, OAuthCallbackRequest

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    pages_data = [
        {
            "id": "page_111",
            "name": "My Brand Page",
            "access_token": "page_access_token_aaa",
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
    platforms_upserted = [call.args[2] for call in mock_upsert.call_args_list]
    assert "meta_pending" not in platforms_upserted


async def test_meta_callback_multi_page_stores_pending():
    """meta_oauth_callback with 2+ pages stores meta_pending row, returns 200 with page_selection_required."""
    from app.routers.publishing import meta_oauth_callback, OAuthCallbackRequest
    from fastapi.responses import JSONResponse

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

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.meta_integration.exchange_code_for_short_lived_token",
              AsyncMock(return_value="short_token")),
        patch("app.routers.publishing.meta_integration.exchange_short_lived_for_long_lived_token",
              AsyncMock(return_value="long_token")),
        patch("app.routers.publishing.meta_integration.discover_accounts",
              AsyncMock(return_value=pages_data)),
        patch("app.routers.publishing.upsert_connection", AsyncMock()) as mock_upsert,
    ):
        result = await meta_oauth_callback(
            client_id=client.id,
            body=OAuthCallbackRequest(code="auth_code"),
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert isinstance(result, JSONResponse)
    assert result.status_code == 200
    body = json.loads(result.body)
    assert body["status"] == "page_selection_required"
    assert len(body["pages"]) == 2
    assert body["pages"][0]["has_instagram"] is True
    assert body["pages"][0]["instagram_username"] == "brand1"

    platforms_upserted = [call.args[2] for call in mock_upsert.call_args_list]
    assert "meta_pending" in platforms_upserted
    assert "instagram" not in platforms_upserted
    assert "facebook_page" not in platforms_upserted


async def test_meta_callback_multi_page_has_instagram_false():
    """meta_oauth_callback multi-page: page without instagram has has_instagram=False and instagram_username=None."""
    from app.routers.publishing import meta_oauth_callback, OAuthCallbackRequest
    from fastapi.responses import JSONResponse

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    pages_data = [
        {
            "id": "page_111",
            "name": "Brand Page 1",
            "access_token": "page_token_aaa",
            # no instagram_business_account
        },
        {
            "id": "page_333",
            "name": "Brand Page 2",
            "access_token": "page_token_bbb",
        },
    ]

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.meta_integration.exchange_code_for_short_lived_token",
              AsyncMock(return_value="short_token")),
        patch("app.routers.publishing.meta_integration.exchange_short_lived_for_long_lived_token",
              AsyncMock(return_value="long_token")),
        patch("app.routers.publishing.meta_integration.discover_accounts",
              AsyncMock(return_value=pages_data)),
        patch("app.routers.publishing.upsert_connection", AsyncMock()),
    ):
        result = await meta_oauth_callback(
            client_id=client.id,
            body=OAuthCallbackRequest(code="auth_code"),
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert isinstance(result, JSONResponse)
    body = json.loads(result.body)
    assert body["pages"][0]["has_instagram"] is False
    assert body["pages"][0]["instagram_username"] is None


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


# ── publish_instagram_feed_post ───────────────────────────────────────────────

async def test_publish_instagram_success():
    """publish_instagram_feed_post: container created, polled FINISHED, media published, media_id returned."""
    from app.integrations.meta import publish_instagram_feed_post

    container_resp = _make_httpx_response(200, {"id": "container_abc"})
    status_finished = _make_httpx_response(200, {"status_code": "FINISHED"})
    publish_resp = _make_httpx_response(200, {"id": "media_xyz"})

    with patch("app.integrations.threads_auth.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=lambda url, **kw: container_resp if "media_publish" not in url else publish_resp)
        mock_client.get = AsyncMock(return_value=status_finished)
        mock_cls.return_value = mock_client

        media_id = await publish_instagram_feed_post(
            instagram_user_id="ig_222",
            page_access_token="page_tok",
            image_url="https://example.com/image.jpg",
            caption="Hello world",
        )

    assert media_id == "media_xyz"


async def test_publish_instagram_container_error():
    """publish_instagram_feed_post raises PlatformError when container status is ERROR."""
    from app.integrations.meta import publish_instagram_feed_post
    from app.core.exceptions import PlatformError

    container_resp = _make_httpx_response(200, {"id": "container_abc"})
    status_error = _make_httpx_response(200, {"status_code": "ERROR"})

    with patch("app.integrations.threads_auth.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=container_resp)
        mock_client.get = AsyncMock(return_value=status_error)
        mock_cls.return_value = mock_client

        with pytest.raises(PlatformError) as exc_info:
            await publish_instagram_feed_post("ig_222", "page_tok", "https://example.com/img.jpg", "caption")

    assert exc_info.value.status_code == 422
    assert "container processing failed" in exc_info.value.message


async def test_publish_instagram_container_timeout():
    """publish_instagram_feed_post raises 408 PlatformError after 6 IN_PROGRESS polls."""
    from app.integrations.meta import publish_instagram_feed_post
    from app.core.exceptions import PlatformError

    container_resp = _make_httpx_response(200, {"id": "container_abc"})
    status_in_progress = _make_httpx_response(200, {"status_code": "IN_PROGRESS"})

    with patch("httpx.AsyncClient") as mock_cls, patch("asyncio.sleep", AsyncMock()):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=container_resp)
        mock_client.get = AsyncMock(return_value=status_in_progress)
        mock_cls.return_value = mock_client

        with pytest.raises(PlatformError) as exc_info:
            await publish_instagram_feed_post("ig_222", "page_tok", "https://example.com/img.jpg", "caption")

    assert exc_info.value.status_code == 408
    assert "timed out" in exc_info.value.message


async def test_publish_instagram_rate_limit():
    """publish_instagram_feed_post raises PlatformError(429) when media_publish returns 429."""
    from app.integrations.meta import publish_instagram_feed_post
    from app.core.exceptions import PlatformError

    container_resp = _make_httpx_response(200, {"id": "container_abc"})
    status_finished = _make_httpx_response(200, {"status_code": "FINISHED"})
    rate_limit_resp = _make_httpx_response(429, {"error": {"message": "Application request limit reached"}})

    with patch("app.integrations.threads_auth.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=lambda url, **kw: container_resp if "media_publish" not in url else rate_limit_resp)
        mock_client.get = AsyncMock(return_value=status_finished)
        mock_cls.return_value = mock_client

        with pytest.raises(PlatformError) as exc_info:
            await publish_instagram_feed_post("ig_222", "page_tok", "https://example.com/img.jpg", "caption")

    assert exc_info.value.status_code == 429


async def test_publish_instagram_caption_truncated_at_2200():
    """publish_instagram_feed_post truncates caption to 2200 chars before API call."""
    from app.integrations.meta import publish_instagram_feed_post

    long_caption = "x" * 3000
    container_resp = _make_httpx_response(200, {"id": "container_abc"})
    status_finished = _make_httpx_response(200, {"status_code": "FINISHED"})
    publish_resp = _make_httpx_response(200, {"id": "media_xyz"})

    captured_data = {}

    async def capture_post(url, data=None, **kwargs):
        if data and "caption" in data:
            captured_data["caption"] = data["caption"]
        if "media_publish" in url:
            return publish_resp
        return container_resp

    with patch("app.integrations.threads_auth.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=capture_post)
        mock_client.get = AsyncMock(return_value=status_finished)
        mock_cls.return_value = mock_client

        await publish_instagram_feed_post("ig_222", "page_tok", "https://example.com/img.jpg", long_caption)

    assert len(captured_data["caption"]) == 2200


async def test_dispatch_publish_instagram_platform_independence():
    """dispatch_publish: instagram failure does not affect x result."""
    from app.services.publishing import dispatch_publish
    from app.core.exceptions import PlatformError

    campaign_id = uuid.uuid4()
    job_id = uuid.uuid4()
    client_id = uuid.uuid4()

    mock_campaign = MagicMock()
    mock_campaign.client_id = client_id
    mock_campaign.x_post = "test tweet"
    mock_campaign.linkedin_post = "test caption"
    mock_campaign.image_url = "https://example.com/img.jpg"
    mock_campaign.scheduled_at = None
    mock_campaign.status = "approved"

    from app.core.security import encrypt_credential
    ig_creds = json.dumps({"instagram_user_id": "ig_222", "page_access_token": "page_tok", "username": "mybrand"})
    x_creds = json.dumps({"access_token": "x_tok", "refresh_token": "x_ref"})

    def make_connection(platform, creds_json):
        conn = MagicMock()
        conn.platform = platform
        conn.encrypted_credentials = encrypt_credential(creds_json)
        return conn

    connections = [make_connection("instagram", ig_creds), make_connection("x", x_creds)]

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=mock_campaign)),
        patch("app.services.publishing.get_published_platforms_for_campaign", AsyncMock(return_value=set())),
        patch("app.services.publishing.get_connections_for_client", AsyncMock(return_value=connections)),
        patch("app.services.publishing.meta_integration.publish_instagram_feed_post",
              AsyncMock(side_effect=PlatformError("instagram", 500, "Internal error"))),
        patch("app.services.publishing.twitter_integration.create_tweet", AsyncMock()),
        patch("app.services.publishing._refresh_x_token_if_needed",
              AsyncMock(return_value={"access_token": "x_tok"})),
    ):
        db = AsyncMock()
        results = await dispatch_publish(db, campaign_id, job_id, platforms=["instagram", "x"])

    assert "x" in results and results["x"] == "success"
    assert "instagram" in results
    assert results["instagram"] != "success"


# ── publish_facebook_page_post ────────────────────────────────────────────────

async def test_publish_facebook_page_success():
    """publish_facebook_page_post: POST to /{page_id}/feed, returns post_id."""
    from app.integrations.meta import publish_facebook_page_post

    post_resp = _make_httpx_response(200, {"id": "page_post_abc"})

    captured = {}

    async def fake_post(url, data=None, **kwargs):
        captured["url"] = url
        captured["data"] = data
        return post_resp

    with patch("app.integrations.threads_auth.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=fake_post)
        mock_cls.return_value = mock_client

        post_id = await publish_facebook_page_post("page_111", "page_tok", "Hello world")

    assert post_id == "page_post_abc"
    assert "page_111/feed" in captured["url"]
    assert captured["data"]["message"] == "Hello world"
    assert "link" not in captured["data"]


async def test_publish_facebook_page_with_image():
    """publish_facebook_page_post: link field included when image_url provided."""
    from app.integrations.meta import publish_facebook_page_post

    post_resp = _make_httpx_response(200, {"id": "post_xyz"})
    captured = {}

    async def fake_post(url, data=None, **kwargs):
        captured["data"] = data
        return post_resp

    with patch("app.integrations.threads_auth.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=fake_post)
        mock_cls.return_value = mock_client

        await publish_facebook_page_post("page_111", "page_tok", "Hello", "https://example.com/img.jpg")

    assert captured["data"]["link"] == "https://example.com/img.jpg"


async def test_publish_facebook_page_no_image():
    """publish_facebook_page_post: link field absent when image_url is None."""
    from app.integrations.meta import publish_facebook_page_post

    post_resp = _make_httpx_response(200, {"id": "post_xyz"})
    captured = {}

    async def fake_post(url, data=None, **kwargs):
        captured["data"] = data
        return post_resp

    with patch("app.integrations.threads_auth.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=fake_post)
        mock_cls.return_value = mock_client

        await publish_facebook_page_post("page_111", "page_tok", "Hello", None)

    assert "link" not in captured["data"]


async def test_publish_facebook_page_401():
    """publish_facebook_page_post: PlatformError(401) with reconnect message on expired token."""
    from app.integrations.meta import publish_facebook_page_post
    from app.core.exceptions import PlatformError

    error_resp = _make_httpx_response(401, {"error": {"message": "Invalid OAuth access token"}})

    with patch("app.integrations.threads_auth.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=error_resp)
        mock_cls.return_value = mock_client

        with pytest.raises(PlatformError) as exc_info:
            await publish_facebook_page_post("page_111", "expired_tok", "Hello")

    assert exc_info.value.status_code == 401
    assert "reconnect" in exc_info.value.message.lower()


async def test_publish_facebook_page_no_linkedin_post():
    """dispatch_publish: facebook_page skipped when campaign has no linkedin_post."""
    from app.services.publishing import dispatch_publish

    campaign_id = uuid.uuid4()
    job_id = uuid.uuid4()
    client_id = uuid.uuid4()

    mock_campaign = MagicMock()
    mock_campaign.client_id = client_id
    mock_campaign.linkedin_post = None
    mock_campaign.image_url = "https://example.com/img.jpg"
    mock_campaign.status = "approved"

    from app.core.security import encrypt_credential
    fb_creds = json.dumps({"page_id": "page_111", "page_name": "My Page", "page_access_token": "page_tok"})

    def make_connection(platform, creds_json):
        conn = MagicMock()
        conn.platform = platform
        conn.encrypted_credentials = encrypt_credential(creds_json)
        return conn

    connections = [make_connection("facebook_page", fb_creds)]

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=mock_campaign)),
        patch("app.services.publishing.get_published_platforms_for_campaign", AsyncMock(return_value=set())),
        patch("app.services.publishing.get_connections_for_client", AsyncMock(return_value=connections)),
    ):
        db = AsyncMock()
        results = await dispatch_publish(db, campaign_id, job_id, platforms=["facebook_page"])

    assert results.get("facebook_page") == "skipped"


async def test_dispatch_publish_facebook_page_independence():
    """dispatch_publish: facebook_page failure does not affect instagram result."""
    from app.services.publishing import dispatch_publish
    from app.core.exceptions import PlatformError

    campaign_id = uuid.uuid4()
    job_id = uuid.uuid4()
    client_id = uuid.uuid4()

    mock_campaign = MagicMock()
    mock_campaign.client_id = client_id
    mock_campaign.linkedin_post = "test post"
    mock_campaign.image_url = "https://example.com/img.jpg"
    mock_campaign.status = "approved"

    from app.core.security import encrypt_credential
    fb_creds = json.dumps({"page_id": "page_111", "page_name": "My Page", "page_access_token": "page_tok"})
    ig_creds = json.dumps({"instagram_user_id": "ig_222", "page_access_token": "page_tok", "username": "mybrand"})

    def make_connection(platform, creds_json):
        conn = MagicMock()
        conn.platform = platform
        conn.encrypted_credentials = encrypt_credential(creds_json)
        return conn

    connections = [make_connection("facebook_page", fb_creds), make_connection("instagram", ig_creds)]

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=mock_campaign)),
        patch("app.services.publishing.get_published_platforms_for_campaign", AsyncMock(return_value=set())),
        patch("app.services.publishing.get_connections_for_client", AsyncMock(return_value=connections)),
        patch("app.services.publishing.meta_integration.publish_facebook_page_post",
              AsyncMock(side_effect=PlatformError("facebook_page", 500, "Server error"))),
        patch("app.services.publishing.meta_integration.publish_instagram_feed_post", AsyncMock(return_value="media_xyz")),
    ):
        db = AsyncMock()
        results = await dispatch_publish(db, campaign_id, job_id, platforms=["facebook_page", "instagram"])

    assert "instagram" in results and results["instagram"] == "success"
    assert "facebook_page" in results and results["facebook_page"] != "success"


# ── publish_threads_post ──────────────────────────────────────────────────────

async def test_publish_threads_success():
    """publish_threads_post: container created with media_type=TEXT, published, post_id returned."""
    from app.integrations.meta import publish_threads_post

    container_resp = _make_httpx_response(200, {"id": "container_th_abc"})
    publish_resp = _make_httpx_response(200, {"id": "threads_post_xyz"})

    call_count = 0

    async def fake_post(url, data=None, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            assert data["media_type"] == "TEXT"
            assert data["text"] == "Hello threads"
            return container_resp
        return publish_resp

    with patch("httpx.AsyncClient") as mock_cls, patch("asyncio.sleep", AsyncMock()):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=fake_post)
        mock_cls.return_value = mock_client

        post_id = await publish_threads_post("th_444", "user_tok", "Hello threads")

    assert post_id == "threads_post_xyz"
    assert call_count == 2


async def test_publish_threads_401():
    """publish_threads_post: PlatformError(401) with reconnect message when threads_publish returns 401."""
    from app.integrations.meta import publish_threads_post
    from app.core.exceptions import PlatformError

    container_resp = _make_httpx_response(200, {"id": "container_th_abc"})
    auth_error = _make_httpx_response(401, {"error": {"message": "Invalid OAuth access token"}})

    call_count = 0

    async def fake_post(url, data=None, **kwargs):
        nonlocal call_count
        call_count += 1
        return container_resp if call_count == 1 else auth_error

    with patch("httpx.AsyncClient") as mock_cls, patch("asyncio.sleep", AsyncMock()):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=fake_post)
        mock_cls.return_value = mock_client

        with pytest.raises(PlatformError) as exc_info:
            await publish_threads_post("th_444", "expired_tok", "Hello")

    assert exc_info.value.status_code == 401
    assert "reconnect" in exc_info.value.message.lower()


async def test_publish_threads_429():
    """publish_threads_post: PlatformError(429) with rate-limit message on threads_publish 429."""
    from app.integrations.meta import publish_threads_post
    from app.core.exceptions import PlatformError

    container_resp = _make_httpx_response(200, {"id": "container_th_abc"})
    rate_limit = _make_httpx_response(429, {"error": {"message": "Application request limit reached"}})

    call_count = 0

    async def fake_post(url, data=None, **kwargs):
        nonlocal call_count
        call_count += 1
        return container_resp if call_count == 1 else rate_limit

    with patch("httpx.AsyncClient") as mock_cls, patch("asyncio.sleep", AsyncMock()):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=fake_post)
        mock_cls.return_value = mock_client

        with pytest.raises(PlatformError) as exc_info:
            await publish_threads_post("th_444", "user_tok", "Hello")

    assert exc_info.value.status_code == 429
    assert "rate limit" in exc_info.value.message.lower()


async def test_publish_threads_no_x_post():
    """dispatch_publish: threads skipped when campaign has no x_post."""
    from app.services.publishing import dispatch_publish

    campaign_id = uuid.uuid4()
    job_id = uuid.uuid4()
    client_id = uuid.uuid4()

    mock_campaign = MagicMock()
    mock_campaign.client_id = client_id
    mock_campaign.x_post = None
    mock_campaign.status = "approved"

    from app.core.security import encrypt_credential
    th_creds = json.dumps({"threads_user_id": "th_444", "username": "mybrand", "user_access_token": "user_tok"})

    def make_connection(platform, creds_json):
        conn = MagicMock()
        conn.platform = platform
        conn.encrypted_credentials = encrypt_credential(creds_json)
        return conn

    connections = [make_connection("threads", th_creds)]

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=mock_campaign)),
        patch("app.services.publishing.get_published_platforms_for_campaign", AsyncMock(return_value=set())),
        patch("app.services.publishing.get_connections_for_client", AsyncMock(return_value=connections)),
    ):
        db = AsyncMock()
        results = await dispatch_publish(db, campaign_id, job_id, platforms=["threads"])

    assert results.get("threads") == "skipped"


async def test_dispatch_publish_threads_independence():
    """dispatch_publish: threads failure does not affect linkedin result."""
    from app.services.publishing import dispatch_publish
    from app.core.exceptions import PlatformError

    campaign_id = uuid.uuid4()
    job_id = uuid.uuid4()
    client_id = uuid.uuid4()

    mock_campaign = MagicMock()
    mock_campaign.client_id = client_id
    mock_campaign.x_post = "Hello threads"
    mock_campaign.linkedin_post = "LinkedIn post text"
    mock_campaign.image_url = None
    mock_campaign.blog_html = None
    mock_campaign.status = "approved"

    from app.core.security import encrypt_credential
    th_creds = json.dumps({"threads_user_id": "th_444", "username": "mybrand", "user_access_token": "user_tok"})
    li_creds = json.dumps({"access_token": "li_tok"})

    def make_connection(platform, creds_json):
        conn = MagicMock()
        conn.platform = platform
        conn.encrypted_credentials = encrypt_credential(creds_json)
        return conn

    connections = [make_connection("threads", th_creds), make_connection("linkedin", li_creds)]

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=mock_campaign)),
        patch("app.services.publishing.get_published_platforms_for_campaign", AsyncMock(return_value=set())),
        patch("app.services.publishing.get_connections_for_client", AsyncMock(return_value=connections)),
        patch("app.services.publishing.meta_integration.publish_threads_post",
              AsyncMock(side_effect=PlatformError("threads", 500, "Server error"))),
        patch("app.services.publishing.linkedin_integration.create_ugc_post", AsyncMock()),
    ):
        db = AsyncMock()
        results = await dispatch_publish(db, campaign_id, job_id, platforms=["threads", "linkedin"])

    assert "linkedin" in results and results["linkedin"] == "success"
    assert "threads" in results and results["threads"] != "success"


async def test_publish_threads_container_no_id():
    """publish_threads_post: PlatformError raised when container creation returns no id."""
    from app.integrations.meta import publish_threads_post
    from app.core.exceptions import PlatformError

    no_id_resp = _make_httpx_response(200, {})

    with patch("app.integrations.threads_auth.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=no_id_resp)
        mock_cls.return_value = mock_client

        with pytest.raises(PlatformError) as exc_info:
            await publish_threads_post("th_444", "user_tok", "Hello")

    assert exc_info.value.status_code == 200
    assert "no id" in exc_info.value.message


# ── threads_auth.py ───────────────────────────────────────────────────────────

async def test_threads_auth_exchange_code_success():
    """exchange_code_for_short_lived_token returns access_token on 200."""
    from app.integrations.threads_auth import exchange_code_for_short_lived_token

    resp = _make_httpx_response(200, {"access_token": "short_tok_abc"})

    with patch("app.integrations.threads_auth.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=resp)
        mock_cls.return_value = mock_client

        result = await exchange_code_for_short_lived_token("auth_code", "https://example.com/callback")

    assert result == "short_tok_abc"


async def test_threads_auth_exchange_code_non_200_raises():
    """exchange_code_for_short_lived_token raises PlatformError on non-200."""
    from app.integrations.threads_auth import exchange_code_for_short_lived_token
    from app.core.exceptions import PlatformError

    resp = _make_httpx_response(400, {"error_message": "Invalid code"})

    with patch("app.integrations.threads_auth.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=resp)
        mock_cls.return_value = mock_client

        with pytest.raises(PlatformError) as exc_info:
            await exchange_code_for_short_lived_token("bad_code", "https://example.com/callback")

    assert exc_info.value.status_code == 400


async def test_threads_auth_exchange_long_lived_success():
    """exchange_short_lived_for_long_lived_token returns access_token on 200."""
    from app.integrations.threads_auth import exchange_short_lived_for_long_lived_token

    resp = _make_httpx_response(200, {"access_token": "long_tok_xyz"})

    with patch("app.integrations.threads_auth.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=resp)
        mock_cls.return_value = mock_client

        result = await exchange_short_lived_for_long_lived_token("short_tok")

    assert result == "long_tok_xyz"


async def test_threads_auth_get_user_success():
    """get_threads_user returns id and username on 200."""
    from app.integrations.threads_auth import get_threads_user

    resp = _make_httpx_response(200, {"id": "12345", "username": "mybrand"})

    with patch("app.integrations.threads_auth.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=resp)
        mock_cls.return_value = mock_client

        result = await get_threads_user("long_tok")

    assert result.get("id") == "12345"
    assert result.get("username") == "mybrand"


async def test_threads_auth_get_user_non_200_raises():
    """get_threads_user raises PlatformError on non-200."""
    from app.integrations.threads_auth import get_threads_user
    from app.core.exceptions import PlatformError

    resp = _make_httpx_response(401, {"error": {"message": "Invalid token"}})

    with patch("app.integrations.threads_auth.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=resp)
        mock_cls.return_value = mock_client

        with pytest.raises(PlatformError) as exc_info:
            await get_threads_user("bad_tok")

    assert exc_info.value.status_code == 401


# ── threads_oauth_callback endpoint ──────────────────────────────────────────

async def test_threads_callback_success():
    """threads_oauth_callback stores credentials and returns connected_platforms=['threads']."""
    from app.routers.publishing import threads_oauth_callback, OAuthCallbackRequest

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.threads_auth.exchange_code_for_short_lived_token",
              AsyncMock(return_value="short_tok")),
        patch("app.routers.publishing.threads_auth.exchange_short_lived_for_long_lived_token",
              AsyncMock(return_value="long_tok")),
        patch("app.routers.publishing.threads_auth.get_threads_user",
              AsyncMock(return_value={"id": "th_111", "username": "mybrand"})),
        patch("app.routers.publishing.upsert_connection", AsyncMock()) as mock_upsert,
    ):
        result = await threads_oauth_callback(
            client_id=client.id,
            body=OAuthCallbackRequest(code="auth_code"),
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result == {"connected_platforms": ["threads"]}
    mock_upsert.assert_called_once()
    assert mock_upsert.call_args.args[2] == "threads"
    # 4th arg is encrypted credential bytes -- verify it's non-empty
    assert mock_upsert.call_args.args[3]


async def test_threads_callback_token_exchange_failure_raises_400():
    """threads_oauth_callback raises 400 when short-lived token exchange fails."""
    from app.routers.publishing import threads_oauth_callback, OAuthCallbackRequest
    from app.core.exceptions import PlatformError

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.threads_auth.exchange_code_for_short_lived_token",
              AsyncMock(side_effect=PlatformError("threads", 400, "Invalid code"))),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await threads_oauth_callback(
                client_id=client.id,
                body=OAuthCallbackRequest(code="bad_code"),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "TOKEN_EXCHANGE_FAILED"


async def test_threads_callback_empty_user_id_raises_422():
    """threads_oauth_callback raises 422 when Threads user ID is empty."""
    from app.routers.publishing import threads_oauth_callback, OAuthCallbackRequest

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.threads_auth.exchange_code_for_short_lived_token",
              AsyncMock(return_value="short_tok")),
        patch("app.routers.publishing.threads_auth.exchange_short_lived_for_long_lived_token",
              AsyncMock(return_value="long_tok")),
        patch("app.routers.publishing.threads_auth.get_threads_user",
              AsyncMock(return_value={"id": "", "username": ""})),
        patch("app.routers.publishing.upsert_connection", AsyncMock()),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await threads_oauth_callback(
                client_id=client.id,
                body=OAuthCallbackRequest(code="auth_code"),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["error"]["code"] == "USER_FETCH_FAILED"


# ── threads_auth.py: renew_long_lived_token ───────────────────────────────────

async def test_renew_long_lived_token_success():
    """renew_long_lived_token returns new token string on 200."""
    from app.integrations.threads_auth import renew_long_lived_token

    resp = _make_httpx_response(200, {"access_token": "renewed_tok_xyz", "token_type": "bearer"})

    with patch("app.integrations.threads_auth.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=resp)
        mock_cls.return_value = mock_client

        result = await renew_long_lived_token("existing_long_lived_tok")

    assert result == "renewed_tok_xyz"


async def test_renew_long_lived_token_non_200():
    """renew_long_lived_token raises PlatformError("threads", 400, ...) on non-200."""
    from app.integrations.threads_auth import renew_long_lived_token
    from app.core.exceptions import PlatformError

    resp = _make_httpx_response(400, {"error": {"message": "Invalid OAuth access token"}})

    with patch("app.integrations.threads_auth.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=resp)
        mock_cls.return_value = mock_client

        with pytest.raises(PlatformError) as exc_info:
            await renew_long_lived_token("bad_tok")

    assert exc_info.value.platform == "threads"
    assert exc_info.value.status_code == 400
    assert "Invalid OAuth access token" in exc_info.value.message


async def test_renew_long_lived_token_no_access_token():
    """renew_long_lived_token raises PlatformError("threads", 200, ...) when body has no access_token."""
    from app.integrations.threads_auth import renew_long_lived_token
    from app.core.exceptions import PlatformError

    resp = _make_httpx_response(200, {})

    with patch("app.integrations.threads_auth.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=resp)
        mock_cls.return_value = mock_client

        with pytest.raises(PlatformError) as exc_info:
            await renew_long_lived_token("some_tok")

    assert exc_info.value.platform == "threads"
    assert exc_info.value.status_code == 200
    assert "no access_token" in exc_info.value.message


# ── publishing.py: _refresh_threads_token_if_needed ──────────────────────────

async def test_refresh_threads_token_fresh():
    """_refresh_threads_token_if_needed returns cred unchanged when token is 10 days old."""
    from app.services.publishing import _refresh_threads_token_if_needed
    from datetime import datetime, timezone, timedelta

    acquired = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    cred = {"user_access_token": "tok", "token_acquired_at": acquired}
    db = AsyncMock()
    client_id = uuid.uuid4()

    with patch("app.services.publishing.threads_auth_integration.renew_long_lived_token") as mock_renew:
        result = await _refresh_threads_token_if_needed(cred, db, client_id)

    assert result is cred
    mock_renew.assert_not_called()


async def test_refresh_threads_token_stale():
    """_refresh_threads_token_if_needed renews, updates cred, and calls upsert_connection when 55 days old."""
    from app.services.publishing import _refresh_threads_token_if_needed
    from datetime import datetime, timezone, timedelta

    acquired = (datetime.now(timezone.utc) - timedelta(days=55)).isoformat()
    cred = {
        "threads_user_id": "th_111",
        "username": "mybrand",
        "user_access_token": "old_tok",
        "token_acquired_at": acquired,
    }
    db = AsyncMock()
    client_id = uuid.uuid4()

    with (
        patch("app.services.publishing.threads_auth_integration.renew_long_lived_token",
              AsyncMock(return_value="new_tok")) as mock_renew,
        patch("app.services.publishing.upsert_connection", AsyncMock()) as mock_upsert,
    ):
        result = await _refresh_threads_token_if_needed(cred, db, client_id)

    mock_renew.assert_called_once_with("old_tok")
    mock_upsert.assert_called_once()
    assert result["user_access_token"] == "new_tok"
    assert result["token_acquired_at"] != acquired


async def test_refresh_threads_token_no_timestamp():
    """_refresh_threads_token_if_needed returns cred unchanged when token_acquired_at is absent."""
    from app.services.publishing import _refresh_threads_token_if_needed

    cred = {"threads_user_id": "th_111", "user_access_token": "old_tok"}
    db = AsyncMock()
    client_id = uuid.uuid4()

    with patch("app.services.publishing.threads_auth_integration.renew_long_lived_token") as mock_renew:
        result = await _refresh_threads_token_if_needed(cred, db, client_id)

    assert result is cred
    mock_renew.assert_not_called()


async def test_refresh_threads_token_renewal_failure():
    """_refresh_threads_token_if_needed is non-fatal: returns original cred on PlatformError, logs warning."""
    from app.services.publishing import _refresh_threads_token_if_needed
    from app.core.exceptions import PlatformError
    from datetime import datetime, timezone, timedelta

    acquired = (datetime.now(timezone.utc) - timedelta(days=55)).isoformat()
    cred = {"user_access_token": "old_tok", "token_acquired_at": acquired}
    db = AsyncMock()
    client_id = uuid.uuid4()

    with (
        patch("app.services.publishing.threads_auth_integration.renew_long_lived_token",
              AsyncMock(side_effect=PlatformError("threads", 400, "Token expired"))),
        patch("app.services.publishing.upsert_connection", AsyncMock()) as mock_upsert,
        patch("app.services.publishing.logger") as mock_logger,
    ):
        result = await _refresh_threads_token_if_needed(cred, db, client_id)

    assert result is cred
    mock_upsert.assert_not_called()
    mock_logger.warning.assert_called_once()


async def test_refresh_threads_token_timeout():
    """_refresh_threads_token_if_needed is non-fatal: returns original cred on TimeoutException."""
    from app.services.publishing import _refresh_threads_token_if_needed
    from datetime import datetime, timezone, timedelta
    import httpx

    acquired = (datetime.now(timezone.utc) - timedelta(days=55)).isoformat()
    cred = {"user_access_token": "old_tok", "token_acquired_at": acquired}
    db = AsyncMock()
    client_id = uuid.uuid4()

    with (
        patch("app.services.publishing.threads_auth_integration.renew_long_lived_token",
              AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))),
        patch("app.services.publishing.upsert_connection", AsyncMock()) as mock_upsert,
        patch("app.services.publishing.logger") as mock_logger,
    ):
        result = await _refresh_threads_token_if_needed(cred, db, client_id)

    assert result is cred
    mock_upsert.assert_not_called()
    mock_logger.warning.assert_called_once()


# ── meta.py: renew_long_lived_user_token ─────────────────────────────────────

async def test_renew_long_lived_user_token_success():
    """renew_long_lived_user_token returns new Facebook user token on 200."""
    from app.integrations.meta import renew_long_lived_user_token

    resp = _make_httpx_response(200, {"access_token": "renewed_fb_tok", "token_type": "bearer"})

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=resp)
        mock_cls.return_value = mock_client

        result = await renew_long_lived_user_token("existing_fb_long_lived_tok")

    assert result == "renewed_fb_tok"


async def test_renew_long_lived_user_token_failure():
    """renew_long_lived_user_token raises PlatformError("Meta", 401, ...) on 401."""
    from app.integrations.meta import renew_long_lived_user_token
    from app.core.exceptions import PlatformError

    resp = _make_httpx_response(401, {"error": {"message": "Invalid OAuth access token"}})

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=resp)
        mock_cls.return_value = mock_client

        with pytest.raises(PlatformError) as exc_info:
            await renew_long_lived_user_token("expired_fb_tok")

    assert exc_info.value.platform == "Meta"
    assert exc_info.value.status_code == 401


async def test_renew_long_lived_user_token_no_access_token():
    """renew_long_lived_user_token raises PlatformError("Meta", 200, ...) when body has no access_token."""
    from app.integrations.meta import renew_long_lived_user_token
    from app.core.exceptions import PlatformError

    resp = _make_httpx_response(200, {})

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=resp)
        mock_cls.return_value = mock_client

        with pytest.raises(PlatformError) as exc_info:
            await renew_long_lived_user_token("some_fb_tok")

    assert exc_info.value.platform == "Meta"
    assert exc_info.value.status_code == 200
    assert "no access_token" in exc_info.value.message


# ── publishing.py: meta_select_page ──────────────────────────────────────────

def _make_pending_row(pages, long_lived_token="long_tok", age_seconds=0):
    """Build a mock meta_pending connection row with encrypted credentials."""
    from app.core.security import encrypt_credential
    from datetime import datetime, timezone, timedelta

    created_at = (datetime.now(timezone.utc) - timedelta(seconds=age_seconds)).isoformat()
    cred = json.dumps({
        "long_lived_token": long_lived_token,
        "pages": pages,
        "created_at": created_at,
    })
    conn = MagicMock()
    conn.platform = "meta_pending"
    conn.encrypted_credentials = encrypt_credential(cred)
    return conn


async def test_meta_select_page_success():
    """meta_select_page: upserts instagram+facebook_page+threads, deletes meta_pending, returns 201."""
    from app.routers.publishing import meta_select_page, MetaSelectPageRequest

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    pages = [
        {
            "id": "page_111",
            "name": "Brand Page 1",
            "access_token": "page_tok_aaa",
            "instagram_user_id": "ig_222",
            "instagram_username": "brand1",
        },
        {
            "id": "page_333",
            "name": "Brand Page 2",
            "access_token": "page_tok_bbb",
            "instagram_user_id": "ig_444",
            "instagram_username": "brand2",
        },
    ]
    pending_conn = _make_pending_row(pages, long_lived_token="long_tok")

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_connections_for_client",
              AsyncMock(return_value=[pending_conn])),
        patch("app.routers.publishing.meta_integration.discover_threads_user_id",
              AsyncMock(return_value="th_555")),
        patch("app.routers.publishing.upsert_connection", AsyncMock()) as mock_upsert,
        patch("app.routers.publishing.delete_connection", AsyncMock()) as mock_delete,
    ):
        result = await meta_select_page(
            client_id=client.id,
            body=MetaSelectPageRequest(page_id="page_111"),
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert "instagram" in result["connected_platforms"]
    assert "facebook_page" in result["connected_platforms"]
    assert "threads" in result["connected_platforms"]

    platforms_upserted = [call.args[2] for call in mock_upsert.call_args_list]
    assert "instagram" in platforms_upserted
    assert "facebook_page" in platforms_upserted
    assert "threads" in platforms_upserted

    mock_delete.assert_called_once()
    assert mock_delete.call_args.args[2] == "meta_pending"


async def test_meta_select_page_no_pending_returns_404():
    """meta_select_page: raises 404 NO_PENDING_CONNECTION when no meta_pending row exists."""
    from app.routers.publishing import meta_select_page, MetaSelectPageRequest

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_connections_for_client",
              AsyncMock(return_value=[])),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await meta_select_page(
                client_id=client.id,
                body=MetaSelectPageRequest(page_id="page_111"),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["error"]["code"] == "NO_PENDING_CONNECTION"


async def test_meta_select_page_expired_returns_410():
    """meta_select_page: raises 410 PENDING_CONNECTION_EXPIRED when created_at > 10 minutes ago."""
    from app.routers.publishing import meta_select_page, MetaSelectPageRequest

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    pages = [{"id": "page_111", "name": "Page", "access_token": "tok",
               "instagram_user_id": None, "instagram_username": None}]
    pending_conn = _make_pending_row(pages, age_seconds=700)

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_connections_for_client",
              AsyncMock(return_value=[pending_conn])),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await meta_select_page(
                client_id=client.id,
                body=MetaSelectPageRequest(page_id="page_111"),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 410
    assert exc_info.value.detail["error"]["code"] == "PENDING_CONNECTION_EXPIRED"


async def test_meta_select_page_invalid_page_id_returns_400():
    """meta_select_page: raises 400 INVALID_PAGE_SELECTION when page_id not in stored pages."""
    from app.routers.publishing import meta_select_page, MetaSelectPageRequest

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    pages = [{"id": "page_111", "name": "Page", "access_token": "tok",
               "instagram_user_id": None, "instagram_username": None}]
    pending_conn = _make_pending_row(pages)

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_connections_for_client",
              AsyncMock(return_value=[pending_conn])),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await meta_select_page(
                client_id=client.id,
                body=MetaSelectPageRequest(page_id="page_WRONG"),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "INVALID_PAGE_SELECTION"


async def test_meta_select_page_no_instagram_page():
    """meta_select_page: page with no instagram_user_id upserts only facebook_page, deletes meta_pending."""
    from app.routers.publishing import meta_select_page, MetaSelectPageRequest

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    pages = [
        {"id": "page_111", "name": "Page Only", "access_token": "tok",
         "instagram_user_id": None, "instagram_username": None},
        {"id": "page_222", "name": "Page 2", "access_token": "tok2",
         "instagram_user_id": None, "instagram_username": None},
    ]
    pending_conn = _make_pending_row(pages)

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_connections_for_client",
              AsyncMock(return_value=[pending_conn])),
        patch("app.routers.publishing.upsert_connection", AsyncMock()) as mock_upsert,
        patch("app.routers.publishing.delete_connection", AsyncMock()) as mock_delete,
    ):
        result = await meta_select_page(
            client_id=client.id,
            body=MetaSelectPageRequest(page_id="page_111"),
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert "facebook_page" in result["connected_platforms"]
    assert "instagram" not in result["connected_platforms"]
    assert "threads" not in result["connected_platforms"]

    platforms_upserted = [call.args[2] for call in mock_upsert.call_args_list]
    assert "facebook_page" in platforms_upserted
    assert "instagram" not in platforms_upserted

    mock_delete.assert_called_once()
    assert mock_delete.call_args.args[2] == "meta_pending"


# ── dispatch_publish: github_pages exclusion ──────────────────────────────────

@pytest.mark.asyncio
async def test_dispatch_publish_excludes_github_pages_when_no_platforms_filter():
    """dispatch_publish: github_pages connection excluded from 'publish all' path (AC 1, AC 4)."""
    from app.services.publishing import dispatch_publish
    from app.core.security import encrypt_credential

    campaign_id = uuid.uuid4()
    job_id = uuid.uuid4()
    client_id = uuid.uuid4()

    mock_campaign = MagicMock()
    mock_campaign.client_id = client_id
    mock_campaign.x_post = "test tweet"
    mock_campaign.linkedin_post = "test linkedin caption"
    mock_campaign.image_url = None
    mock_campaign.scheduled_at = None
    mock_campaign.status = "approved"

    fb_creds = json.dumps({"page_id": "pg_111", "page_access_token": "page_tok", "page_name": "Test Page"})
    gh_creds = json.dumps({})

    def make_connection(platform, creds_json):
        conn = MagicMock()
        conn.platform = platform
        conn.encrypted_credentials = encrypt_credential(creds_json)
        return conn

    connections = [
        make_connection("facebook_page", fb_creds),
        make_connection("github_pages", gh_creds),
    ]

    mock_fb_publish = AsyncMock(return_value="fb_post_id")

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=mock_campaign)),
        patch("app.services.publishing.get_published_platforms_for_campaign", AsyncMock(return_value=set())),
        patch("app.services.publishing.get_connections_for_client", AsyncMock(return_value=connections)),
        patch("app.services.publishing.meta_integration.publish_facebook_page_post", mock_fb_publish),
    ):
        db = AsyncMock()
        results = await dispatch_publish(db, campaign_id, job_id, platforms=None)

    assert "github_pages" not in results
    assert "facebook_page" in results
    assert results["facebook_page"] == "success"
    mock_fb_publish.assert_called_once()


@pytest.mark.asyncio
async def test_dispatch_publish_includes_github_pages_when_explicitly_requested():
    """dispatch_publish: github_pages NOT excluded when caller passes it explicitly (AC 2)."""
    from app.services.publishing import dispatch_publish
    from app.core.security import encrypt_credential

    campaign_id = uuid.uuid4()
    job_id = uuid.uuid4()
    client_id = uuid.uuid4()

    mock_campaign = MagicMock()
    mock_campaign.client_id = client_id
    mock_campaign.x_post = "test tweet"
    mock_campaign.linkedin_post = "test linkedin caption"
    mock_campaign.image_url = None
    mock_campaign.scheduled_at = None
    mock_campaign.status = "approved"

    fb_creds = json.dumps({"page_id": "pg_111", "page_access_token": "page_tok", "page_name": "Test Page"})
    gh_creds = json.dumps({})

    def make_connection(platform, creds_json):
        conn = MagicMock()
        conn.platform = platform
        conn.encrypted_credentials = encrypt_credential(creds_json)
        return conn

    connections = [
        make_connection("facebook_page", fb_creds),
        make_connection("github_pages", gh_creds),
    ]

    mock_fb_publish = AsyncMock(return_value="fb_post_id")
    mock_gh_publish = AsyncMock(side_effect=Exception("No repository selected"))

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=mock_campaign)),
        patch("app.services.publishing.get_published_platforms_for_campaign", AsyncMock(return_value=set())),
        patch("app.services.publishing.get_connections_for_client", AsyncMock(return_value=connections)),
        patch("app.services.publishing.meta_integration.publish_facebook_page_post", mock_fb_publish),
        patch("app.services.publishing._publish_github", mock_gh_publish),
    ):
        db = AsyncMock()
        results = await dispatch_publish(db, campaign_id, job_id, platforms=["github_pages"])

    assert "github_pages" in results
    assert "facebook_page" not in results
