"""Integration tests for twitter.py — upload_media and create_tweet_with_media."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest


def _mock_response(status_code: int, json_body: dict | None = None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body or {}
    resp.text = str(json_body or {})
    return resp


# ---------------------------------------------------------------------------
# upload_media — INIT/APPEND/FINALIZE happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upload_media_chunked():
    """INIT → APPEND (1 chunk) → FINALIZE; assert media_id returned."""
    from app.integrations.twitter import upload_media

    media_id = "1234567890"
    image_bytes = b"x" * 512  # small: single chunk

    init_resp = _mock_response(201, {"data": {"id": media_id}})
    append_resp = _mock_response(204)
    finalize_resp = _mock_response(200, {"data": {"id": media_id, "processing_info": {}}})

    call_responses = [init_resp, append_resp, finalize_resp]
    call_idx = 0

    async def mock_post(url, **kwargs):
        nonlocal call_idx
        resp = call_responses[call_idx]
        call_idx += 1
        return resp

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = mock_post

    with patch("app.integrations.twitter.httpx.AsyncClient", return_value=mock_client):
        result = await upload_media("tok123", image_bytes)

    assert result == media_id


@pytest.mark.asyncio
async def test_upload_media_multiple_chunks():
    """Image larger than 1MB triggers multiple APPEND calls."""
    from app.integrations.twitter import upload_media

    media_id = "9999"
    image_bytes = b"x" * (2 * 1_048_576 + 100)  # 2MB + 100 bytes → 3 chunks

    responses = [
        _mock_response(201, {"data": {"id": media_id}}),  # INIT
        _mock_response(204),  # APPEND 0
        _mock_response(204),  # APPEND 1
        _mock_response(204),  # APPEND 2
        _mock_response(200),  # FINALIZE
    ]
    call_idx = 0

    async def mock_post(url, **kwargs):
        nonlocal call_idx
        resp = responses[call_idx]
        call_idx += 1
        return resp

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = mock_post

    with patch("app.integrations.twitter.httpx.AsyncClient", return_value=mock_client):
        result = await upload_media("tok", image_bytes)

    assert result == media_id
    assert call_idx == 5  # INIT + 3×APPEND + FINALIZE


@pytest.mark.asyncio
async def test_upload_media_init_failure_raises():
    """Non-2xx INIT response raises PlatformError."""
    from app.integrations.twitter import upload_media
    from app.core.exceptions import PlatformError

    init_resp = _mock_response(500, {})

    async def mock_post(url, **kwargs):
        return init_resp

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = mock_post

    with patch("app.integrations.twitter.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(PlatformError) as exc_info:
            await upload_media("tok", b"data")

    assert exc_info.value.platform == "X"
    assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# create_tweet_with_media
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_tweet_with_media():
    """Happy path: 201 with media_ids in request body, returns tweet ID."""
    from app.integrations.twitter import create_tweet_with_media

    tweet_id = "tweet_abc"
    captured_json = {}

    async def mock_post(url, *, headers, json, params, **kwargs):
        captured_json.update(json)
        return _mock_response(201, {"data": {"id": tweet_id}})

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = mock_post

    with patch("app.integrations.twitter.httpx.AsyncClient", return_value=mock_client):
        result = await create_tweet_with_media("tok", "Hello world", "media_123")

    assert result == tweet_id
    assert "media" in captured_json
    assert captured_json["media"]["media_ids"] == ["media_123"]


@pytest.mark.asyncio
async def test_create_tweet_with_media_truncates_text():
    """Text longer than 280 chars is truncated before posting."""
    from app.integrations.twitter import create_tweet_with_media

    captured_json = {}

    async def mock_post(url, *, headers, json, params, **kwargs):
        captured_json.update(json)
        return _mock_response(201, {"data": {"id": "t1"}})

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = mock_post

    long_text = "a" * 500
    with patch("app.integrations.twitter.httpx.AsyncClient", return_value=mock_client):
        await create_tweet_with_media("tok", long_text, "mid")

    assert len(captured_json["text"]) == 280


@pytest.mark.asyncio
async def test_create_tweet_with_media_non_201_raises():
    """Non-201 response raises PlatformError."""
    from app.integrations.twitter import create_tweet_with_media
    from app.core.exceptions import PlatformError

    async def mock_post(url, **kwargs):
        return _mock_response(403, {"detail": "forbidden"})

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = mock_post

    with patch("app.integrations.twitter.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(PlatformError) as exc_info:
            await create_tweet_with_media("tok", "text", "mid")

    assert exc_info.value.status_code == 403
