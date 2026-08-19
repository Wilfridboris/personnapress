"""Integration tests for linkedin.py — exchange_code_for_token, upload_image, create_post_with_image."""
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
# exchange_code_for_token — returns dict with access_token and scope
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_exchange_code_for_token_returns_access_token_and_scope():
    """Happy path: token endpoint returns access_token and scope; both are returned in dict."""
    from app.integrations.linkedin import exchange_code_for_token

    token_response = {
        "access_token": "AQX_test_token",
        "expires_in": 5184000,
        "scope": "openid,profile,w_member_social,r_organization_admin,w_organization_social",
        "token_type": "Bearer",
    }

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=_mock_response(200, token_response))

    with patch("app.integrations.linkedin.httpx.AsyncClient", return_value=mock_client):
        result = await exchange_code_for_token("auth_code", "https://example.com/callback")

    assert result["access_token"] == "AQX_test_token"
    assert result["scope"] == "openid,profile,w_member_social,r_organization_admin,w_organization_social"
    assert "w_organization_social" in result["scope"]


@pytest.mark.asyncio
async def test_exchange_code_for_token_missing_scope_returns_empty_string():
    """If LinkedIn omits scope in response, scope defaults to empty string (legacy compat)."""
    from app.integrations.linkedin import exchange_code_for_token

    token_response = {"access_token": "AQX_legacy_token"}

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=_mock_response(200, token_response))

    with patch("app.integrations.linkedin.httpx.AsyncClient", return_value=mock_client):
        result = await exchange_code_for_token("auth_code", "https://example.com/callback")

    assert result["access_token"] == "AQX_legacy_token"
    assert result["scope"] == ""


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


# ---------------------------------------------------------------------------
# create_ugc_post — org_id parameter (AC 7)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_ugc_post_personal_calls_userinfo():
    """With org_id=None, create_ugc_post fetches /v2/userinfo and uses urn:li:person."""
    from app.integrations.linkedin import create_ugc_post

    captured_json = {}
    userinfo_called = []

    async def mock_get(url, **kwargs):
        userinfo_called.append(url)
        return _mock_response(200, {"sub": "person123"})

    async def mock_post(url, *, json, **kwargs):
        captured_json.update(json)
        return _mock_response(201, {}, headers={"x-restli-id": "urn:li:ugcPost:1"})

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = mock_get
    mock_client.post = mock_post

    with patch("app.integrations.linkedin.httpx.AsyncClient", return_value=mock_client):
        result = await create_ugc_post("tok", "<p>html</p>", "text", org_id=None)

    assert result == "urn:li:ugcPost:1"
    assert captured_json["author"] == "urn:li:person:person123"
    assert any("userinfo" in u for u in userinfo_called), "/v2/userinfo must be called for personal posting"


@pytest.mark.asyncio
async def test_create_ugc_post_org_skips_userinfo():
    """With org_id provided, create_ugc_post skips /v2/userinfo and uses urn:li:organization."""
    from app.integrations.linkedin import create_ugc_post

    captured_json = {}
    called_urls = []

    async def mock_get(url, **kwargs):
        called_urls.append(url)
        return _mock_response(200, {"sub": "should_not_be_called"})

    async def mock_post(url, *, json, **kwargs):
        captured_json.update(json)
        return _mock_response(201, {}, headers={"x-restli-id": "urn:li:ugcPost:2"})

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = mock_get
    mock_client.post = mock_post

    with patch("app.integrations.linkedin.httpx.AsyncClient", return_value=mock_client):
        result = await create_ugc_post("tok", "<p>html</p>", "text", org_id="123456")

    assert result == "urn:li:ugcPost:2"
    assert captured_json["author"] == "urn:li:organization:123456"
    assert not any("userinfo" in u for u in called_urls), "/v2/userinfo must NOT be called when posting as org"
