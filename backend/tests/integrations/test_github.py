"""Tests for integrations/github.py."""
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
