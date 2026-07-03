"""Tests for dispatch_publish_for_platform in services/publishing.py."""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.security import encrypt_credential


def _make_campaign(client_id=None):
    c = MagicMock()
    c.id = uuid.uuid4()
    c.client_id = client_id or uuid.uuid4()
    c.blog_html = "<p>Content</p>"
    c.x_post = "Tweet text"
    c.linkedin_post = "LinkedIn text"
    return c


def _make_connection(platform="wordpress", creds=None):
    conn = MagicMock()
    conn.platform = platform
    if creds is None:
        creds = {"site_url": "https://wp.example.com", "username": "admin", "credential": "pass"}
    conn.encrypted_credentials = encrypt_credential(json.dumps(creds))
    return conn


async def test_dispatch_retry_single_platform_success():
    from app.services.publishing import dispatch_publish_for_platform

    campaign = _make_campaign()
    conn = _make_connection("wordpress")
    db = AsyncMock()

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.services.publishing.get_connection_for_platform", AsyncMock(return_value=conn)),
        patch("app.services.publishing.wordpress_integration.publish_post", AsyncMock(return_value="https://wp.example.com/post")),
    ):
        result = await dispatch_publish_for_platform(db, campaign.id, "wordpress")

    assert result == {"wordpress": "success"}


async def test_dispatch_retry_merges_results_all_success():
    """After retry succeeds, merged dict should be all_success."""
    from app.services.publishing import dispatch_publish_for_platform

    campaign = _make_campaign()
    conn = _make_connection("linkedin", creds={"access_token": "token"})
    db = AsyncMock()

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.services.publishing.get_connection_for_platform", AsyncMock(return_value=conn)),
        patch("app.services.publishing.linkedin_integration.create_ugc_post", AsyncMock(return_value=None)),
    ):
        result = await dispatch_publish_for_platform(db, campaign.id, "linkedin")

    existing = {"wordpress": "success", "x": "success"}
    merged = {**existing, **result}
    all_success = all(v == "success" for v in merged.values()) and bool(merged)
    assert all_success is True


async def test_dispatch_retry_still_failing():
    """If retry fails, result should be error string, not 'success'."""
    from app.services.publishing import dispatch_publish_for_platform
    from app.core.exceptions import PlatformError

    campaign = _make_campaign()
    conn = _make_connection("wordpress")
    db = AsyncMock()

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.services.publishing.get_connection_for_platform", AsyncMock(return_value=conn)),
        patch(
            "app.services.publishing.wordpress_integration.publish_post",
            AsyncMock(side_effect=PlatformError("wordpress", 401, "check your Application Password")),
        ),
    ):
        result = await dispatch_publish_for_platform(db, campaign.id, "wordpress")

    assert "wordpress" in result
    assert result["wordpress"] != "success"
    assert "returned 401" in result["wordpress"]
    assert "check your Application Password" in result["wordpress"]


async def test_dispatch_retry_no_connection():
    from app.services.publishing import dispatch_publish_for_platform

    campaign = _make_campaign()
    db = AsyncMock()

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.services.publishing.get_connection_for_platform", AsyncMock(return_value=None)),
    ):
        result = await dispatch_publish_for_platform(db, campaign.id, "wordpress")

    assert result == {"wordpress": "no platform connection found"}
