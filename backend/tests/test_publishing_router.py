"""Unit tests for routers/publishing.py — platform connection endpoints."""
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_client(user_id=None, client_id=None):
    c = MagicMock()
    c.id = client_id or uuid.uuid4()
    c.user_id = user_id or uuid.uuid4()
    return c


def _make_connection(client_id=None, platform="wordpress", cred_json=None):
    pc = MagicMock()
    pc.id = uuid.uuid4()
    pc.client_id = client_id or uuid.uuid4()
    pc.platform = platform
    if cred_json is None:
        cred_json = json.dumps({"site_url": "https://example.com", "username": "admin", "credential": "pass"})
    from app.core.security import encrypt_credential
    pc.encrypted_credentials = encrypt_credential(cred_json)
    pc.created_at = datetime(2026, 7, 2, 10, 0, 0, tzinfo=timezone.utc)
    pc.updated_at = datetime(2026, 7, 2, 10, 0, 0, tzinfo=timezone.utc)
    return pc


# ── GET /clients/{id}/connections — empty ─────────────────────────────────────

async def test_list_connections_empty():
    from app.routers.publishing import list_platform_connections

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_connections_for_client", AsyncMock(return_value=[])),
    ):
        result = await list_platform_connections(
            client_id=client.id,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert "items" in result
    assert len(result["items"]) == 5
    assert all(not item["connected"] for item in result["items"])
    platforms = [i["platform"] for i in result["items"]]
    assert "wordpress" in platforms
    assert "webflow" in platforms
    assert "x" in platforms
    assert "linkedin" in platforms
    assert "github_pages" in platforms


# ── GET /clients/{id}/connections — with wordpress ────────────────────────────

async def test_list_connections_with_wordpress():
    from app.routers.publishing import list_platform_connections

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    conn = _make_connection(client_id=client.id, platform="wordpress")
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_connections_for_client", AsyncMock(return_value=[conn])),
    ):
        result = await list_platform_connections(
            client_id=client.id,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    wp_item = next(i for i in result["items"] if i["platform"] == "wordpress")
    assert wp_item["connected"] is True
    assert "example.com" in wp_item["account_identifier"]


# ── POST /clients/{id}/connections — wordpress success ────────────────────────

async def test_create_wordpress_connection_success():
    from app.routers.publishing import ConnectionCreate, create_platform_connection

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()
    stored_conn = _make_connection(client_id=client.id, platform="wordpress")

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.wordpress_integration.validate_credentials", AsyncMock(return_value="https://example.com")),
        patch("app.routers.publishing.upsert_connection", AsyncMock(return_value=stored_conn)),
    ):
        result = await create_platform_connection(
            client_id=client.id,
            body=ConnectionCreate(
                platform="wordpress",
                site_url="https://example.com",
                credential="pass pass pass pass",
                username="admin",
            ),
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result["platform"] == "wordpress"
    assert result["connected"] is True
    assert result["account_identifier"] == "https://example.com"


# ── POST /clients/{id}/connections — wordpress 401 ───────────────────────────

async def test_create_wordpress_connection_401():
    from app.routers.publishing import ConnectionCreate, create_platform_connection
    from app.core.exceptions import PlatformError

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch(
            "app.routers.publishing.wordpress_integration.validate_credentials",
            AsyncMock(side_effect=PlatformError("wordpress", 401, "check your Application Password")),
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await create_platform_connection(
                client_id=client.id,
                body=ConnectionCreate(
                    platform="wordpress",
                    site_url="https://example.com",
                    credential="wrong",
                    username="admin",
                ),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "CREDENTIAL_VALIDATION_FAILED"


# ── POST /clients/{id}/connections — webflow success ─────────────────────────

async def test_create_webflow_connection_success():
    from app.routers.publishing import ConnectionCreate, create_platform_connection

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()
    wf_cred = json.dumps({"token": "tok", "collection_id": "col123"})
    stored_conn = _make_connection(client_id=client.id, platform="webflow", cred_json=wf_cred)

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.upsert_connection", AsyncMock(return_value=stored_conn)),
    ):
        result = await create_platform_connection(
            client_id=client.id,
            body=ConnectionCreate(platform="webflow", token="tok", collection_id="col123"),
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result["platform"] == "webflow"
    assert result["connected"] is True
    assert result["account_identifier"] == "col123"


# ── GET /clients/{id}/webflow/collections ─────────────────────────────────────

async def test_get_webflow_collections():
    from app.routers.publishing import get_webflow_collections

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()
    collections = [{"id": "c1", "name": "Blog Posts"}, {"id": "c2", "name": "News"}]

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.webflow_integration.fetch_collections", AsyncMock(return_value=collections)),
    ):
        result = await get_webflow_collections(
            client_id=client.id,
            token="mytoken",
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result["collections"] == collections


# ── DELETE /clients/{id}/connections/{platform} ───────────────────────────────

async def test_delete_connection():
    from app.routers.publishing import delete_platform_connection

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.delete_connection", AsyncMock(return_value=True)),
    ):
        result = await delete_platform_connection(
            client_id=client.id,
            platform="wordpress",
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result is None


async def test_delete_connection_not_found():
    from app.routers.publishing import delete_platform_connection

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.delete_connection", AsyncMock(return_value=False)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await delete_platform_connection(
                client_id=client.id,
                platform="wordpress",
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 404


# ── POST /clients/{id}/connections/x/callback ────────────────────────────────

async def test_x_oauth_callback_success():
    from app.routers.publishing import OAuthCallbackRequest, x_oauth_callback

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    x_cred = json.dumps({"access_token": "at", "refresh_token": "rt", "handle": "twitteruser"})
    stored = _make_connection(client_id=client.id, platform="x", cred_json=x_cred)

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch(
            "app.routers.publishing.twitter_integration.exchange_code_for_tokens",
            AsyncMock(return_value={"access_token": "at", "refresh_token": "rt"}),
        ),
        patch(
            "app.routers.publishing.twitter_integration.get_user_handle",
            AsyncMock(return_value="twitteruser"),
        ),
        patch("app.routers.publishing.upsert_connection", AsyncMock(return_value=stored)),
    ):
        result = await x_oauth_callback(
            client_id=client.id,
            body=OAuthCallbackRequest(code="code123", code_verifier="verifier"),
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result["platform"] == "x"
    assert result["connected"] is True
    assert result["account_identifier"] == "@twitteruser"


async def test_x_oauth_callback_token_exchange_failure():
    from app.routers.publishing import OAuthCallbackRequest, x_oauth_callback
    from app.core.exceptions import PlatformError

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch(
            "app.routers.publishing.twitter_integration.exchange_code_for_tokens",
            AsyncMock(side_effect=PlatformError("X", 400, "invalid code")),
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await x_oauth_callback(
                client_id=client.id,
                body=OAuthCallbackRequest(code="bad", code_verifier="v"),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "TOKEN_EXCHANGE_FAILED"


# ── POST /clients/{id}/connections/linkedin/callback ─────────────────────────

async def test_linkedin_oauth_callback_success():
    from app.routers.publishing import OAuthCallbackRequest, linkedin_oauth_callback

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    li_cred = json.dumps({"access_token": "lat", "name": "John Doe"})
    stored = _make_connection(client_id=client.id, platform="linkedin", cred_json=li_cred)

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch(
            "app.routers.publishing.linkedin_integration.exchange_code_for_token",
            AsyncMock(return_value="lat"),
        ),
        patch(
            "app.routers.publishing.linkedin_integration.get_user_name",
            AsyncMock(return_value="John Doe"),
        ),
        patch("app.routers.publishing.upsert_connection", AsyncMock(return_value=stored)),
    ):
        result = await linkedin_oauth_callback(
            client_id=client.id,
            body=OAuthCallbackRequest(code="licode"),
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result["platform"] == "linkedin"
    assert result["connected"] is True
    assert result["account_identifier"] == "John Doe"


async def test_linkedin_oauth_callback_failure():
    from app.routers.publishing import OAuthCallbackRequest, linkedin_oauth_callback
    from app.core.exceptions import PlatformError

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch(
            "app.routers.publishing.linkedin_integration.exchange_code_for_token",
            AsyncMock(side_effect=PlatformError("LinkedIn", 400, "token exchange failed")),
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await linkedin_oauth_callback(
                client_id=client.id,
                body=OAuthCallbackRequest(code="bad"),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "TOKEN_EXCHANGE_FAILED"


async def test_ownership_check_returns_404_for_other_user():
    from app.routers.publishing import list_platform_connections

    owner_id = uuid.uuid4()
    requester_id = uuid.uuid4()
    client = _make_client(user_id=owner_id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await list_platform_connections(
                client_id=client.id,
                current_user={"user_id": str(requester_id)},
                db=db,
            )

    assert exc_info.value.status_code == 404


async def test_x_oauth_callback_missing_code_verifier():
    from app.routers.publishing import OAuthCallbackRequest, x_oauth_callback

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await x_oauth_callback(
                client_id=client.id,
                body=OAuthCallbackRequest(code="code123"),  # no code_verifier
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "MISSING_CODE_VERIFIER"


async def test_x_oauth_callback_empty_access_token():
    from app.routers.publishing import OAuthCallbackRequest, x_oauth_callback

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch(
            "app.routers.publishing.twitter_integration.exchange_code_for_tokens",
            AsyncMock(return_value={"token_type": "bearer"}),  # missing access_token
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await x_oauth_callback(
                client_id=client.id,
                body=OAuthCallbackRequest(code="code123", code_verifier="verifier"),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "TOKEN_EXCHANGE_FAILED"


# ── WordPress.com callback ────────────────────────────────────────────────────

async def test_wordpress_com_callback_success():
    from app.routers.publishing import wordpress_com_oauth_callback, WpComCallbackRequest

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()
    tokens = {"access_token": "tok123", "blog_id": "987", "blog_url": "https://mysite.wordpress.com"}

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.wordpress_com_integration.exchange_code_for_tokens", AsyncMock(return_value=tokens)),
        patch("app.routers.publishing.upsert_connection", AsyncMock()),
    ):
        result = await wordpress_com_oauth_callback(
            client_id=client.id,
            body=WpComCallbackRequest(code="code123"),
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result["platform"] == "wordpress-com"
    assert result["connected"] is True
    assert result["account_identifier"] == "https://mysite.wordpress.com"


async def test_wordpress_com_callback_token_exchange_failure():
    from app.routers.publishing import wordpress_com_oauth_callback, WpComCallbackRequest
    from app.core.exceptions import PlatformError

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch(
            "app.routers.publishing.wordpress_com_integration.exchange_code_for_tokens",
            AsyncMock(side_effect=PlatformError("wordpress-com", 400, "bad code")),
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await wordpress_com_oauth_callback(
                client_id=client.id,
                body=WpComCallbackRequest(code="bad"),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "TOKEN_EXCHANGE_FAILED"


async def test_list_connections_with_wpcom():
    from app.routers.publishing import list_platform_connections

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    wpcom_cred = json.dumps({"access_token": "tok", "blog_id": "123", "blog_url": "https://mysite.wordpress.com"})
    conn = _make_connection(client_id=client.id, platform="wordpress-com", cred_json=wpcom_cred)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_connections_for_client", AsyncMock(return_value=[conn])),
    ):
        result = await list_platform_connections(
            client_id=client.id,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert len(result["items"]) == 5
    wp_item = next(i for i in result["items"] if i["platform"] == "wordpress")
    assert wp_item["connected"] is True
    assert wp_item.get("connected_via") == "wordpress-com"
    assert wp_item["account_identifier"] == "https://mysite.wordpress.com"


async def test_list_connections_prefers_selfhosted_over_wpcom():
    from app.routers.publishing import list_platform_connections

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    sh_conn = _make_connection(client_id=client.id, platform="wordpress")
    wpcom_cred = json.dumps({"access_token": "tok", "blog_id": "123", "blog_url": "https://mysite.wordpress.com"})
    wpcom_conn = _make_connection(client_id=client.id, platform="wordpress-com", cred_json=wpcom_cred)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_connections_for_client", AsyncMock(return_value=[sh_conn, wpcom_conn])),
    ):
        result = await list_platform_connections(
            client_id=client.id,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    wp_item = next(i for i in result["items"] if i["platform"] == "wordpress")
    assert wp_item["connected"] is True
    assert "connected_via" not in wp_item  # self-hosted has no connected_via


async def test_delete_wordpress_com_connection():
    from app.routers.publishing import delete_platform_connection

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.delete_connection", AsyncMock(return_value=True)),
    ):
        result = await delete_platform_connection(
            client_id=client.id,
            platform="wordpress-com",
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result is None  # 204 No Content


async def test_wordpress_com_publish_dispatch():
    from app.services.publishing import dispatch_publish_for_platform

    campaign_id = uuid.uuid4()
    client_id = uuid.uuid4()
    campaign = MagicMock()
    campaign.client_id = client_id
    campaign.blog_html = "<h1>Test</h1>"
    campaign.image_url = None
    campaign.x_post = None
    campaign.linkedin_post = None

    wpcom_cred = json.dumps({"access_token": "tok", "blog_id": "123", "blog_url": "https://mysite.wordpress.com"})
    conn = _make_connection(client_id=client_id, platform="wordpress-com", cred_json=wpcom_cred)
    db = AsyncMock()

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.services.publishing.get_connection_for_platform", AsyncMock(return_value=conn)),
        patch("app.services.publishing.wordpress_com_integration.publish_post", AsyncMock(return_value="https://post.url")),
    ):
        result = await dispatch_publish_for_platform(db, campaign_id, "wordpress-com")

    assert result == {"wordpress-com": "success"}
