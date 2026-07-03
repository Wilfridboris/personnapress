"""Tests for integrations/wordpress.py publish_post."""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx


def _make_campaign(image_url=None):
    c = MagicMock()
    c.blog_html = "<h1>My Post Title</h1><p>Content here.</p>"
    c.image_url = image_url
    return c


def _make_creds():
    return {"site_url": "https://wp.example.com", "username": "admin", "credential": "secret123"}


class _MockResponse:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error", request=MagicMock(), response=MagicMock(status_code=self.status_code)
            )

    @property
    def content(self):
        return b"data"

    @property
    def headers(self):
        return {"content-type": "image/png"}


async def test_publish_post_draft_first():
    """Draft-first pattern: create draft, upload image, then publish."""
    from app.integrations.wordpress import publish_post

    campaign = _make_campaign(image_url="https://cdn.example.com/img.png")
    creds = _make_creds()

    draft_resp = _MockResponse(201, {"id": 42})
    img_download_resp = _MockResponse(200, {})
    img_resp = _MockResponse(201, {"id": 99})
    pub_resp = _MockResponse(200, {"link": "https://wp.example.com/my-post-title/"})

    call_count = {"post": 0, "get": 0}

    async def mock_post(url, **kwargs):
        call_count["post"] += 1
        if "posts" in url and call_count["post"] == 1:
            return draft_resp
        elif "media" in url:
            return img_resp
        elif "posts" in url:
            return pub_resp
        return _MockResponse(200, {})

    async def mock_get(url, **kwargs):
        return img_download_resp

    async def mock_patch(url, **kwargs):
        return pub_resp

    with patch("httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=mock_post)
        mock_client.get = AsyncMock(side_effect=mock_get)
        mock_client.patch = AsyncMock(return_value=pub_resp)
        MockClient.return_value = mock_client

        result = await publish_post(creds, campaign)

    assert result == "https://wp.example.com/my-post-title/"
    # Verify post was called (draft + media)
    assert call_count["post"] >= 1


async def test_publish_post_cleanup_on_failure():
    """If publish step fails, DELETE draft is called for cleanup."""
    from app.integrations.wordpress import publish_post
    from app.core.exceptions import PlatformError

    campaign = _make_campaign()
    creds = _make_creds()

    draft_resp = _MockResponse(201, {"id": 77})
    fail_resp = _MockResponse(500, {"code": "rest_post_invalid_id"})
    delete_resp = _MockResponse(200, {"deleted": True, "previous": {}})

    with patch("httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=draft_resp)
        mock_client.patch = AsyncMock(return_value=fail_resp)
        mock_client.delete = AsyncMock(return_value=delete_resp)
        mock_client.get = AsyncMock(return_value=_MockResponse(200, {}))
        MockClient.return_value = mock_client

        with pytest.raises(PlatformError) as exc_info:
            await publish_post(creds, campaign)

    assert exc_info.value.platform == "wordpress"
    assert "draft cleaned up" in exc_info.value.message
    mock_client.delete.assert_called_once()
