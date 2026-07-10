"""Tests for webhook endpoints in routers/webhooks.py."""
import hashlib
import hmac
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request


def _make_github_payload(action="closed", merged=True, pr_url="https://github.com/owner/repo/pull/1") -> bytes:
    return json.dumps({
        "action": action,
        "pull_request": {
            "merged": merged,
            "html_url": pr_url,
        },
    }).encode("utf-8")


def _sign_payload(payload: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256).hexdigest()


def _make_request(payload: bytes, sig: str, event_type: str = "pull_request") -> MagicMock:
    req = MagicMock(spec=Request)
    req.body = AsyncMock(return_value=payload)
    req.headers = {
        "x-hub-signature-256": sig,
        "x-github-event": event_type,
    }
    return req


# ── Signature verification rejects tampered payload ──────────────────────────

@pytest.mark.asyncio
async def test_github_webhook_rejects_bad_signature():
    from fastapi import HTTPException
    from app.routers.webhooks import github_webhook

    payload = _make_github_payload()
    # Sign with wrong secret
    bad_sig = _sign_payload(payload, "wrong-secret")
    req = _make_request(payload, bad_sig)
    db = AsyncMock()

    with patch("app.routers.webhooks.settings") as mock_settings:
        mock_settings.GITHUB_APP_WEBHOOK_SECRET = "correct-secret"
        with pytest.raises(HTTPException) as exc_info:
            await github_webhook(request=req, db=db)

    assert exc_info.value.status_code == 400


# ── Merged PR triggers campaign published transition ─────────────────────────

@pytest.mark.asyncio
async def test_github_webhook_merged_pr_publishes_campaign():
    from app.routers.webhooks import github_webhook

    secret = "test-webhook-secret"
    pr_url = "https://github.com/owner/repo/pull/42"
    payload = _make_github_payload(action="closed", merged=True, pr_url=pr_url)
    sig = _sign_payload(payload, secret)
    req = _make_request(payload, sig)

    campaign = MagicMock()
    campaign.id = uuid.uuid4()
    campaign.status = "approved"
    campaign.github_pr_url = pr_url

    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none = MagicMock(return_value=campaign)

    db = AsyncMock()
    db.execute = AsyncMock(return_value=scalar_result)

    with (
        patch("app.routers.webhooks.settings") as mock_settings,
        patch("app.routers.webhooks.update_campaign_status", AsyncMock()) as mock_update,
    ):
        mock_settings.GITHUB_APP_WEBHOOK_SECRET = secret
        result = await github_webhook(request=req, db=db)

    assert result == {"received": True}
    mock_update.assert_called_once_with(db, campaign.id, "published")
    db.commit.assert_called_once()


# ── Unrecognised PR URL silently returns 200 ─────────────────────────────────

@pytest.mark.asyncio
async def test_github_webhook_unknown_pr_url_ignored():
    from app.routers.webhooks import github_webhook

    secret = "test-webhook-secret"
    pr_url = "https://github.com/owner/repo/pull/999"
    payload = _make_github_payload(action="closed", merged=True, pr_url=pr_url)
    sig = _sign_payload(payload, secret)
    req = _make_request(payload, sig)

    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none = MagicMock(return_value=None)

    db = AsyncMock()
    db.execute = AsyncMock(return_value=scalar_result)

    with patch("app.routers.webhooks.settings") as mock_settings:
        mock_settings.GITHUB_APP_WEBHOOK_SECRET = secret
        result = await github_webhook(request=req, db=db)

    assert result == {"received": True}
    db.commit.assert_not_called()
