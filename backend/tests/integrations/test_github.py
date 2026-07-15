"""Tests for integrations/github.py."""
import base64
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class _MockResponse:
    def __init__(self, status_code: int, data: dict | str):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data

    @property
    def text(self):
        return str(self._data)


@pytest.mark.asyncio
async def test_get_installation_token_success():
    """Returns token and expires_at from GitHub API response."""
    from app.integrations.github import get_installation_token

    fake_resp = _MockResponse(201, {
        "token": "ghs_APPID_JWT_abc123",
        "expires_at": "2026-07-09T12:00:00Z",
    })

    with patch("app.integrations.github.generate_app_jwt", return_value="test-jwt"), \
         patch("httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=fake_resp)
        MockClient.return_value = mock_client

        result = await get_installation_token("12345678")

    assert result["token"] == "ghs_APPID_JWT_abc123"
    assert result["expires_at"] == "2026-07-09T12:00:00Z"


@pytest.mark.asyncio
async def test_get_installation_token_non_200_raises_platform_error():
    """Non-201 response raises PlatformError with github platform."""
    from app.integrations.github import get_installation_token
    from app.core.exceptions import PlatformError

    fake_resp = _MockResponse(401, "Unauthorized")

    with patch("app.integrations.github.generate_app_jwt", return_value="test-jwt"), \
         patch("httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=fake_resp)
        MockClient.return_value = mock_client

        with pytest.raises(PlatformError) as exc_info:
            await get_installation_token("bad-id")

    assert exc_info.value.platform == "github"
    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# slug_from_title
# ---------------------------------------------------------------------------

def test_slug_from_title_basic():
    from app.integrations.github import slug_from_title

    assert slug_from_title("Hello World") == "hello-world"


def test_slug_from_title_strips_special_chars():
    from app.integrations.github import slug_from_title

    assert slug_from_title("10 Tips & Tricks!") == "10-tips-tricks"


def test_slug_from_title_truncates_to_60():
    from app.integrations.github import slug_from_title

    long_title = "word " * 20  # 100 chars with spaces
    result = slug_from_title(long_title)
    assert len(result) <= 60
    assert not result.endswith("-")


def test_slug_from_title_all_special_chars_returns_untitled():
    from app.integrations.github import slug_from_title

    assert slug_from_title("!!! @@@ ###") == "untitled"
    assert slug_from_title("") == "untitled"


# ---------------------------------------------------------------------------
# html_to_markdown
# ---------------------------------------------------------------------------

def test_html_to_markdown_strips_h1():
    from app.integrations.github import html_to_markdown

    html = "<h1>Post Title</h1><p>Body paragraph.</p>"
    result = html_to_markdown(html)
    assert "Post Title" not in result
    assert "Body paragraph" in result


def test_html_to_markdown_preserves_h2_h3():
    from app.integrations.github import html_to_markdown

    html = "<h2>Section</h2><h3>Subsection</h3><p>Text</p>"
    result = html_to_markdown(html)
    assert "## Section" in result
    assert "### Subsection" in result


def test_html_to_markdown_converts_image():
    from app.integrations.github import html_to_markdown

    html = '<img src="https://cdn.example.com/img.png" alt="Featured">'
    result = html_to_markdown(html)
    assert "![Featured](https://cdn.example.com/img.png)" in result


def test_html_to_markdown_converts_figure_with_figcaption():
    """<figure><img><figcaption> produces image markdown and caption text without crashing."""
    from app.integrations.github import html_to_markdown

    html = '<figure><img src="https://cdn.example.com/a.png" alt="Chart"><figcaption>Caption text</figcaption></figure>'
    result = html_to_markdown(html)
    assert "![Chart](https://cdn.example.com/a.png)" in result
    assert "Caption text" in result


def test_html_to_markdown_paragraph_with_inline_img():
    """Paragraph containing inline img produces img markdown inline."""
    from app.integrations.github import html_to_markdown

    html = '<p>Some text</p><img src="https://cdn.example.com/b.png" alt="Chart">'
    result = html_to_markdown(html)
    assert "Some text" in result
    assert "![Chart](https://cdn.example.com/b.png)" in result


# ---------------------------------------------------------------------------
# create_file_commit
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_file_commit_new_file_success():
    """Creates a new file when file does not exist (404 on check)."""
    from app.integrations.github import create_file_commit

    check_resp = _MockResponse(404, "Not Found")
    put_resp = _MockResponse(201, {"commit": {"sha": "abc1234567890"}})

    with patch("httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=check_resp)
        mock_client.put = AsyncMock(return_value=put_resp)
        MockClient.return_value = mock_client

        sha = await create_file_commit("token123", "owner/repo", "_posts/2026-07-09-test.md", "# Hello", "Add post")

    assert sha == "abc1234"


@pytest.mark.asyncio
async def test_create_file_commit_403_raises_platform_error():
    """403 from GitHub raises PlatformError with correct status_code."""
    from app.integrations.github import create_file_commit
    from app.core.exceptions import PlatformError

    check_resp = _MockResponse(404, "Not Found")
    put_resp = _MockResponse(403, "Forbidden")

    with patch("httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=check_resp)
        mock_client.put = AsyncMock(return_value=put_resp)
        MockClient.return_value = mock_client

        with pytest.raises(PlatformError) as exc_info:
            await create_file_commit("token123", "owner/repo", "file.md", "content", "msg")

    assert exc_info.value.status_code == 403
    assert exc_info.value.platform == "github"


@pytest.mark.asyncio
async def test_create_file_commit_422_raises_platform_error():
    """422 from GitHub raises PlatformError."""
    from app.integrations.github import create_file_commit
    from app.core.exceptions import PlatformError

    check_resp = _MockResponse(404, "Not Found")
    put_resp = _MockResponse(422, {"message": "Unprocessable Entity"})

    with patch("httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=check_resp)
        mock_client.put = AsyncMock(return_value=put_resp)
        MockClient.return_value = mock_client

        with pytest.raises(PlatformError) as exc_info:
            await create_file_commit("token123", "owner/repo", "file.md", "content", "msg")

    assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# get_file_contents
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_file_contents_returns_decoded_content():
    from app.integrations.github import get_file_contents

    encoded = base64.b64encode(b"Hello, world!").decode("ascii")
    ok_resp = _MockResponse(200, {"content": encoded + "\n"})

    with patch("httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=ok_resp)
        MockClient.return_value = mock_client

        result = await get_file_contents("token", "owner/repo", "README.md")

    assert result == "Hello, world!"


@pytest.mark.asyncio
async def test_get_file_contents_returns_none_on_404():
    from app.integrations.github import get_file_contents

    not_found = _MockResponse(404, "Not Found")

    with patch("httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=not_found)
        MockClient.return_value = mock_client

        result = await get_file_contents("token", "owner/repo", "missing.md")

    assert result is None
