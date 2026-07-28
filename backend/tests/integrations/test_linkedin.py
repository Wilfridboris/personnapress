"""Integration tests for linkedin.py — upload_image and create_post_with_image."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_response(status_code: int, json_body: dict | None = None, headers: dict | None = None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body or {}
    resp.text = str(json_body or {})
    resp.headers = headers or {}
    return resp


# ---------------------------------------------------------------------------
# upload_image — initializeUpload + PUT binary
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upload_image():
    """Happy path: initializeUpload returns uploadUrl and image URN; PUT succeeds."""
    from app.integrations.linkedin import upload_image

    author_urn = "abc123"
    image_urn = "urn:li:image:C4E10AQF_test"
    upload_url = "https://media.licdn.com/upload/presigned/abc"

    init_body = {"value": {"uploadUrl": upload_url, "image": image_urn}}

    call_log = []

    async def mock_post(url, **kwargs):
        call_log.append(("post", url))
        return _mock_response(200, init_body)

    async def mock_put(url, **kwargs):
        call_log.append(("put", url))
        assert kwargs.get("headers", {}).get("Authorization") is None, "PUT must not include Authorization"
        return _mock_response(201)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = mock_post
    mock_client.put = mock_put

    with patch("app.integrations.linkedin.httpx.AsyncClient", return_value=mock_client):
        result = await upload_image("tok", author_urn, b"imgdata")

    assert result == image_urn
    assert any(op == "put" for op, _ in call_log), "PUT must be called for binary upload"


@pytest.mark.asyncio
async def test_upload_image_init_failure_raises():
    """Non-2xx initializeUpload raises PlatformError."""
    from app.integrations.linkedin import upload_image
    from app.core.exceptions import PlatformError

    async def mock_post(url, **kwargs):
        return _mock_response(400, {"message": "bad request"})

    async def mock_put(url, **kwargs):
        return _mock_response(200)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = mock_post
    mock_client.put = mock_put

    with patch("app.integrations.linkedin.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(PlatformError) as exc_info:
            await upload_image("tok", "urn", b"data")

    assert exc_info.value.platform == "LinkedIn"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_upload_image_put_no_auth_header():
    """The PUT to the pre-signed URL must not include an Authorization header."""
    from app.integrations.linkedin import upload_image

    image_urn = "urn:li:image:test"
    init_body = {"value": {"uploadUrl": "https://presigned.url/upload", "image": image_urn}}
    auth_headers_on_put = []

    async def mock_post(url, **kwargs):
        return _mock_response(200, init_body)

    async def mock_put(url, *, content, headers, **kwargs):
        auth_headers_on_put.append(headers.get("Authorization"))
        return _mock_response(201)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = mock_post
    mock_client.put = mock_put

    with patch("app.integrations.linkedin.httpx.AsyncClient", return_value=mock_client):
        await upload_image("tok", "author", b"data")

    assert auth_headers_on_put[0] is None, "PUT to pre-signed URL must not have Authorization header"


# ---------------------------------------------------------------------------
# create_post_with_image
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_post_with_image():
    """Happy path: 201 response; content.media.id in request body; returns x-restli-id."""
    from app.integrations.linkedin import create_post_with_image

    post_urn = "urn:li:share:9876"
    captured_json = {}

    async def mock_post(url, *, headers, json, **kwargs):
        captured_json.update(json)
        return _mock_response(201, {}, headers={"x-restli-id": post_urn})

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = mock_post

    with patch("app.integrations.linkedin.httpx.AsyncClient", return_value=mock_client):
        result = await create_post_with_image("tok", "author123", "Post text", "urn:li:image:test")

    assert result == post_urn
    assert captured_json["content"]["media"]["id"] == "urn:li:image:test"
    assert captured_json["author"] == "urn:li:person:author123"
    assert captured_json["lifecycleState"] == "PUBLISHED"


@pytest.mark.asyncio
async def test_create_post_with_image_non_201_raises():
    """Non-201 response raises PlatformError."""
    from app.integrations.linkedin import create_post_with_image
    from app.core.exceptions import PlatformError

    async def mock_post(url, **kwargs):
        return _mock_response(400, {"message": "bad request"})

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = mock_post

    with patch("app.integrations.linkedin.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(PlatformError) as exc_info:
            await create_post_with_image("tok", "author", "text", "urn:li:image:x")

    assert exc_info.value.platform == "LinkedIn"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_create_post_with_image_uses_rest_posts_endpoint():
    """create_post_with_image calls /rest/posts, not /v2/ugcPosts."""
    from app.integrations.linkedin import create_post_with_image

    called_url = []

    async def mock_post(url, **kwargs):
        called_url.append(url)
        return _mock_response(201, {}, headers={"x-restli-id": "urn:li:share:1"})

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = mock_post

    with patch("app.integrations.linkedin.httpx.AsyncClient", return_value=mock_client):
        await create_post_with_image("tok", "author", "text", "urn:li:image:x")

    assert called_url[0].endswith("/rest/posts")
    assert "ugcPosts" not in called_url[0]
