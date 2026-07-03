"""Tests for services/publishing.py dispatch_publish."""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch, call
import logging

import pytest


def _make_campaign(client_id=None):
    c = MagicMock()
    c.id = uuid.uuid4()
    c.client_id = client_id or uuid.uuid4()
    c.blog_html = "<h1>Title</h1><p>Body</p>"
    c.x_post = "Check out our new blog post!"
    c.linkedin_post = "Excited to share..."
    c.image_url = "https://cdn.example.com/img.png"
    return c


def _make_connection(platform="wordpress", creds=None):
    from app.core.security import encrypt_credential
    conn = MagicMock()
    conn.platform = platform
    if creds is None:
        creds = {"site_url": "https://wp.example.com", "username": "admin", "credential": "pass"}
    conn.encrypted_credentials = encrypt_credential(json.dumps(creds))
    return conn


async def test_dispatch_publish_all_success():
    from app.services.publishing import dispatch_publish

    campaign = _make_campaign()
    wp_conn = _make_connection("wordpress")
    db = AsyncMock()

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.services.publishing.get_connections_for_client", AsyncMock(return_value=[wp_conn])),
        patch("app.services.publishing.wordpress_integration.publish_post", AsyncMock(return_value="https://wp.example.com/post")),
    ):
        results = await dispatch_publish(db, campaign.id, uuid.uuid4())

    assert results == {"wordpress": "success"}


async def test_dispatch_publish_partial_failure():
    from app.services.publishing import dispatch_publish

    campaign = _make_campaign()
    wp_conn = _make_connection("wordpress")
    x_creds = {"access_token": "token123"}
    x_conn = _make_connection("x", creds=x_creds)
    db = AsyncMock()

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.services.publishing.get_connections_for_client", AsyncMock(return_value=[wp_conn, x_conn])),
        patch("app.services.publishing.wordpress_integration.publish_post", AsyncMock(return_value="")),
        patch("app.services.publishing.twitter_integration.create_tweet", AsyncMock(side_effect=Exception("rate limit exceeded"))),
    ):
        results = await dispatch_publish(db, campaign.id, uuid.uuid4())

    assert results["wordpress"] == "success"
    assert "rate limit exceeded" in results["x"]


async def test_credentials_not_logged(caplog):
    from app.services.publishing import dispatch_publish
    from app.core.security import encrypt_credential

    campaign = _make_campaign()
    secret_password = "super_secret_app_password_12345"
    creds = {"site_url": "https://wp.example.com", "username": "admin", "credential": secret_password}
    wp_conn = MagicMock()
    wp_conn.platform = "wordpress"
    wp_conn.encrypted_credentials = encrypt_credential(json.dumps(creds))
    db = AsyncMock()

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.services.publishing.get_connections_for_client", AsyncMock(return_value=[wp_conn])),
        patch("app.services.publishing.wordpress_integration.publish_post", AsyncMock(side_effect=Exception("connection failed"))),
        caplog.at_level(logging.ERROR, logger="app.services.publishing"),
    ):
        results = await dispatch_publish(db, campaign.id, uuid.uuid4())

    assert results["wordpress"] != "success"
    # The decrypted secret must never appear in any log record
    for record in caplog.records:
        assert secret_password not in record.getMessage()
        assert secret_password not in str(record.args)
