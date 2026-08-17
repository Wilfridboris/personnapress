"""Tests for Story 24.1: published_post record capture on Meta publish paths."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_campaign(client_id=None):
    c = MagicMock()
    c.id = uuid.uuid4()
    c.client_id = client_id or uuid.uuid4()
    c.blog_html = "<h1>Title</h1><p>Body</p>"
    c.x_post = "X post text"
    c.linkedin_post = "LinkedIn post text"
    c.instagram_caption = "Instagram caption"
    c.facebook_post = "Facebook post text"
    c.threads_post = "Threads post text"
    c.image_url = "https://cdn.example.com/img.png"
    return c


def _make_connection(platform, creds):
    from app.core.security import encrypt_credential
    import json
    conn = MagicMock()
    conn.platform = platform
    conn.encrypted_credentials = encrypt_credential(json.dumps(creds))
    return conn


# ---------------------------------------------------------------------------
# Repository: upsert_published_post — insert then update produces one row
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upsert_published_post_insert_then_update_is_idempotent():
    """UPSERT: second call for same (campaign_id, platform) replaces row, no duplicate."""
    from app.db.repositories.published_posts import upsert_published_post
    from sqlalchemy.dialects import postgresql

    campaign_id = uuid.uuid4()
    client_id = uuid.uuid4()
    execute_calls = []
    committed = []

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=lambda stmt: execute_calls.append(stmt) or MagicMock())
    session.commit = AsyncMock(side_effect=lambda: committed.append(True))

    await upsert_published_post(
        session,
        campaign_id=campaign_id,
        client_id=client_id,
        platform="instagram",
        platform_post_id="media_111",
        permalink="https://instagram.com/p/abc",
        published_at=datetime.now(timezone.utc),
    )
    await upsert_published_post(
        session,
        campaign_id=campaign_id,
        client_id=client_id,
        platform="instagram",
        platform_post_id="media_222",
        permalink="https://instagram.com/p/def",
        published_at=datetime.now(timezone.utc),
    )

    assert len(execute_calls) == 2
    assert len(committed) == 2
    # Both stmts must be ON CONFLICT DO UPDATE (not plain INSERT)
    for stmt in execute_calls:
        compiled = str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": False}))
        assert "ON CONFLICT" in compiled


# ---------------------------------------------------------------------------
# Service: Meta platforms capture platform_post_id in dispatch_publish
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dispatch_publish_instagram_captures_media_id():
    """dispatch_publish calls _capture_meta_post with the instagram media_id returned by meta integration."""
    from app.services.publishing import dispatch_publish

    campaign = _make_campaign()
    campaign.status = "approved"
    ig_creds = {"instagram_user_id": "ig_user_123", "page_access_token": "page_tok"}
    ig_conn = _make_connection("instagram", ig_creds)
    db = AsyncMock()

    captured = {}

    async def fake_capture(db_, camp, platform, post_id, token):
        captured["platform"] = platform
        captured["post_id"] = post_id
        captured["token"] = token

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.services.publishing.get_connections_for_client", AsyncMock(return_value=[ig_conn])),
        patch("app.services.publishing.get_published_platforms_for_campaign", AsyncMock(return_value=set())),
        patch("app.services.publishing.meta_integration.publish_instagram_feed_post", AsyncMock(return_value="media_id_abc")),
        patch("app.services.publishing._capture_meta_post", side_effect=fake_capture),
    ):
        results = await dispatch_publish(db, campaign.id, uuid.uuid4())

    assert results.get("instagram") == "success"
    assert captured["platform"] == "instagram"
    assert captured["post_id"] == "media_id_abc"
    assert captured["token"] == "page_tok"


@pytest.mark.asyncio
async def test_dispatch_publish_facebook_captures_post_id():
    """dispatch_publish calls _capture_meta_post with the facebook post_id."""
    from app.services.publishing import dispatch_publish

    campaign = _make_campaign()
    campaign.status = "approved"
    fb_creds = {"page_id": "pg_123", "page_access_token": "page_tok_fb"}
    fb_conn = _make_connection("facebook_page", fb_creds)
    db = AsyncMock()

    captured = {}

    async def fake_capture(db_, camp, platform, post_id, token):
        captured["platform"] = platform
        captured["post_id"] = post_id

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.services.publishing.get_connections_for_client", AsyncMock(return_value=[fb_conn])),
        patch("app.services.publishing.get_published_platforms_for_campaign", AsyncMock(return_value=set())),
        patch("app.services.publishing.meta_integration.publish_facebook_page_post", AsyncMock(return_value="fb_post_xyz")),
        patch("app.services.publishing._capture_meta_post", side_effect=fake_capture),
    ):
        results = await dispatch_publish(db, campaign.id, uuid.uuid4())

    assert results.get("facebook_page") == "success"
    assert captured["platform"] == "facebook_page"
    assert captured["post_id"] == "fb_post_xyz"


@pytest.mark.asyncio
async def test_dispatch_publish_threads_captures_post_id():
    """dispatch_publish calls _capture_meta_post with the threads post_id."""
    from app.services.publishing import dispatch_publish

    campaign = _make_campaign()
    campaign.status = "approved"
    th_creds = {"threads_user_id": "th_user_999", "user_access_token": "th_tok"}
    th_conn = _make_connection("threads", th_creds)
    db = AsyncMock()

    captured = {}

    async def fake_capture(db_, camp, platform, post_id, token):
        captured["platform"] = platform
        captured["post_id"] = post_id
        captured["token"] = token

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.services.publishing.get_connections_for_client", AsyncMock(return_value=[th_conn])),
        patch("app.services.publishing.get_published_platforms_for_campaign", AsyncMock(return_value=set())),
        patch("app.services.publishing._refresh_threads_token_if_needed", AsyncMock(return_value=th_creds)),
        patch("app.services.publishing.meta_integration.publish_threads_post", AsyncMock(return_value="th_post_888")),
        patch("app.services.publishing._capture_meta_post", side_effect=fake_capture),
    ):
        results = await dispatch_publish(db, campaign.id, uuid.uuid4())

    assert results.get("threads") == "success"
    assert captured["platform"] == "threads"
    assert captured["post_id"] == "th_post_888"
    assert captured["token"] == "th_tok"


# ---------------------------------------------------------------------------
# Service: capture also fires in dispatch_publish_for_platform
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dispatch_publish_for_platform_instagram_captures_media_id():
    """dispatch_publish_for_platform also captures the instagram media_id."""
    from app.services.publishing import dispatch_publish_for_platform

    campaign = _make_campaign()
    ig_creds = {"instagram_user_id": "ig_123", "page_access_token": "page_tok2"}
    ig_conn = _make_connection("instagram", ig_creds)
    db = AsyncMock()

    captured = {}

    async def fake_capture(db_, camp, platform, post_id, token):
        captured["platform"] = platform
        captured["post_id"] = post_id

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.services.publishing.get_connection_for_platform", AsyncMock(return_value=ig_conn)),
        patch("app.services.publishing.meta_integration.publish_instagram_feed_post", AsyncMock(return_value="media_retry_abc")),
        patch("app.services.publishing._capture_meta_post", side_effect=fake_capture),
    ):
        result = await dispatch_publish_for_platform(db, campaign.id, "instagram")

    assert result.get("instagram") == "success"
    assert captured["platform"] == "instagram"
    assert captured["post_id"] == "media_retry_abc"


@pytest.mark.asyncio
async def test_dispatch_publish_for_platform_facebook_captures_post_id():
    """dispatch_publish_for_platform captures the facebook_page post_id (AC #9)."""
    from app.services.publishing import dispatch_publish_for_platform

    campaign = _make_campaign()
    fb_creds = {"page_id": "pg_retry_99", "page_access_token": "page_tok_retry"}
    fb_conn = _make_connection("facebook_page", fb_creds)
    db = AsyncMock()

    captured = {}

    async def fake_capture(db_, camp, platform, post_id, token):
        captured["platform"] = platform
        captured["post_id"] = post_id

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.services.publishing.get_connection_for_platform", AsyncMock(return_value=fb_conn)),
        patch("app.services.publishing.meta_integration.publish_facebook_page_post", AsyncMock(return_value="fb_retry_post_xyz")),
        patch("app.services.publishing._capture_meta_post", side_effect=fake_capture),
    ):
        result = await dispatch_publish_for_platform(db, campaign.id, "facebook_page")

    assert result.get("facebook_page") == "success"
    assert captured["platform"] == "facebook_page"
    assert captured["post_id"] == "fb_retry_post_xyz"


@pytest.mark.asyncio
async def test_dispatch_publish_for_platform_threads_captures_post_id():
    """dispatch_publish_for_platform captures the threads post_id (AC #9)."""
    from app.services.publishing import dispatch_publish_for_platform

    campaign = _make_campaign()
    th_creds = {"threads_user_id": "th_retry_user", "user_access_token": "th_tok_retry"}
    th_conn = _make_connection("threads", th_creds)
    db = AsyncMock()

    captured = {}

    async def fake_capture(db_, camp, platform, post_id, token):
        captured["platform"] = platform
        captured["post_id"] = post_id
        captured["token"] = token

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.services.publishing.get_connection_for_platform", AsyncMock(return_value=th_conn)),
        patch("app.services.publishing._refresh_threads_token_if_needed", AsyncMock(return_value=th_creds)),
        patch("app.services.publishing.meta_integration.publish_threads_post", AsyncMock(return_value="th_retry_post_777")),
        patch("app.services.publishing._capture_meta_post", side_effect=fake_capture),
    ):
        result = await dispatch_publish_for_platform(db, campaign.id, "threads")

    assert result.get("threads") == "success"
    assert captured["platform"] == "threads"
    assert captured["post_id"] == "th_retry_post_777"
    assert captured["token"] == "th_tok_retry"


# ---------------------------------------------------------------------------
# Fault isolation: capture failure must not fail the publish (AC #6)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_publish_still_succeeds_when_upsert_raises():
    """When upsert_published_post raises a DB error, publish result is still 'success' (AC #6)."""
    from app.services.publishing import dispatch_publish

    campaign = _make_campaign()
    campaign.status = "approved"
    ig_creds = {"instagram_user_id": "ig_user_fail", "page_access_token": "tok_fail"}
    ig_conn = _make_connection("instagram", ig_creds)
    db = AsyncMock()

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.services.publishing.get_connections_for_client", AsyncMock(return_value=[ig_conn])),
        patch("app.services.publishing.get_published_platforms_for_campaign", AsyncMock(return_value=set())),
        patch("app.services.publishing.meta_integration.publish_instagram_feed_post", AsyncMock(return_value="media_ok")),
        patch("app.services.publishing.meta_integration.fetch_instagram_permalink", AsyncMock(return_value=None)),
        patch("app.services.publishing.upsert_published_post", AsyncMock(side_effect=RuntimeError("DB down"))),
    ):
        results = await dispatch_publish(db, campaign.id, uuid.uuid4())

    assert results.get("instagram") == "success"


@pytest.mark.asyncio
async def test_capture_meta_post_swallows_upsert_failure():
    """_capture_meta_post itself catches upsert errors and never raises."""
    from app.services.publishing import _capture_meta_post

    campaign = _make_campaign()
    db = AsyncMock()

    with (
        patch("app.services.publishing.upsert_published_post", AsyncMock(side_effect=RuntimeError("db error"))),
        patch("app.services.publishing.meta_integration.fetch_instagram_permalink", AsyncMock(return_value=None)),
    ):
        # Must not raise
        await _capture_meta_post(db, campaign, "instagram", "media_123", "tok")


# ---------------------------------------------------------------------------
# Facebook photo post_id: prefer post_id over id (AC #2 dev note)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_publish_facebook_photo_returns_feed_post_id_over_photo_id():
    """publish_facebook_page_post returns post_id (feed) not id (photo object) for photo posts."""
    from app.integrations.meta import publish_facebook_page_post
    import httpx, json

    resp_body = {"id": "photo_111", "post_id": "123456789_987654321"}
    resp = httpx.Response(
        status_code=200,
        content=json.dumps(resp_body).encode(),
        headers={"content-type": "application/json"},
    )

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=resp)
        mock_cls.return_value = mock_client

        result = await publish_facebook_page_post(
            page_id="pg_123",
            page_access_token="tok",
            message="Test caption",
            image_url="https://cdn.example.com/img.png",
        )

    assert result == "123456789_987654321"


@pytest.mark.asyncio
async def test_publish_facebook_text_post_returns_id_when_no_post_id():
    """publish_facebook_page_post returns id for text-only posts (no post_id field)."""
    from app.integrations.meta import publish_facebook_page_post
    import httpx, json

    resp_body = {"id": "pg_123_feed_post_456"}
    resp = httpx.Response(
        status_code=200,
        content=json.dumps(resp_body).encode(),
        headers={"content-type": "application/json"},
    )

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=resp)
        mock_cls.return_value = mock_client

        result = await publish_facebook_page_post(
            page_id="pg_123",
            page_access_token="tok",
            message="Text only post",
            image_url=None,
        )

    assert result == "pg_123_feed_post_456"
