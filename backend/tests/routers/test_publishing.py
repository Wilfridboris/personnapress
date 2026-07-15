"""Tests for GitHub connection endpoints in routers/publishing.py."""
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


def _make_client(user_id=None, client_id=None):
    c = MagicMock()
    c.id = client_id or uuid.uuid4()
    c.user_id = user_id or uuid.uuid4()
    return c


def _make_github_connection(client_id=None, repo_full_name=None):
    from app.core.security import encrypt_credential

    pc = MagicMock()
    pc.id = uuid.uuid4()
    pc.client_id = client_id or uuid.uuid4()
    pc.platform = "github_pages"
    cred = {
        "installation_id": "12345678",
        "installation_token": "ghs_test_token",
        "expires_at": "2026-07-09T13:00:00Z",
        "repo_full_name": repo_full_name,
    }
    pc.encrypted_credentials = encrypt_credential(json.dumps(cred))
    pc.created_at = datetime(2026, 7, 9, 10, 0, 0, tzinfo=timezone.utc)
    pc.updated_at = datetime(2026, 7, 9, 10, 0, 0, tzinfo=timezone.utc)
    return pc


# ── POST /clients/{id}/connections/github — success ──────────────────────────

@pytest.mark.asyncio
async def test_connect_github_success():
    from app.routers.publishing import connect_github, GitHubConnectRequest

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = AsyncMock()
    stored_conn = _make_github_connection(client_id=client.id)

    token_data = {"token": "ghs_test_token", "expires_at": "2026-07-09T13:00:00Z"}

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.github_integration.get_installation_token", AsyncMock(return_value=token_data)),
        patch("app.routers.publishing.upsert_connection", AsyncMock(return_value=stored_conn)),
    ):
        result = await connect_github(
            client_id=client.id,
            body=GitHubConnectRequest(installation_id="12345678"),
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result["platform"] == "github_pages"
    assert result["connected"] is True
    assert result["account_identifier"] is None


# ── POST /clients/{id}/connections/github — 403 wrong owner ──────────────────

@pytest.mark.asyncio
async def test_connect_github_403_wrong_owner():
    from app.routers.publishing import connect_github, GitHubConnectRequest

    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    client = _make_client(user_id=other_user_id)
    db = AsyncMock()

    with patch("app.routers.publishing.get_client", AsyncMock(return_value=client)):
        with pytest.raises(HTTPException) as exc_info:
            await connect_github(
                client_id=client.id,
                body=GitHubConnectRequest(installation_id="12345678"),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 403


# ── POST /clients/{id}/connections/github — 404 client not found ─────────────

@pytest.mark.asyncio
async def test_connect_github_404_client_not_found():
    from app.routers.publishing import connect_github, GitHubConnectRequest

    user_id = uuid.uuid4()
    db = AsyncMock()

    with patch("app.routers.publishing.get_client", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as exc_info:
            await connect_github(
                client_id=uuid.uuid4(),
                body=GitHubConnectRequest(installation_id="12345678"),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 403


# ── POST /campaigns/{id}/publish/github ──────────────────────────────────────

def _make_campaign(client_id=None, status="approved"):
    camp = MagicMock()
    camp.id = uuid.uuid4()
    camp.client_id = client_id or uuid.uuid4()
    camp.status = status
    camp.github_pr_url = None
    return camp


def _make_full_github_connection(client_id=None):
    from app.core.security import encrypt_credential

    pc = MagicMock()
    pc.id = uuid.uuid4()
    pc.client_id = client_id or uuid.uuid4()
    pc.platform = "github_pages"
    cred = {
        "installation_id": "12345678",
        "installation_token": "ghs_test_token",
        "expires_at": "2099-07-09T13:00:00Z",
        "repo_full_name": "owner/repo",
        "detected_framework": "jekyll",
    }
    pc.encrypted_credentials = encrypt_credential(json.dumps(cred))
    return pc


def _make_job(campaign_id=None):
    job = MagicMock()
    job.id = uuid.uuid4()
    job.campaign_id = campaign_id
    return job


@pytest.mark.asyncio
async def test_publish_github_pr_mode_creates_job():
    from fastapi import BackgroundTasks
    from app.routers.publishing import publish_campaign_github, GitHubPublishRequest

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id, status="approved")
    github_conn = _make_full_github_connection(client_id=client.id)
    job = _make_job(campaign_id=campaign.id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_connections_for_client", AsyncMock(return_value=[github_conn])),
        patch("app.routers.publishing.create_job", AsyncMock(return_value=job)),
        patch("app.routers.publishing.publish_github_job", MagicMock()),
    ):
        bg = BackgroundTasks()
        result = await publish_campaign_github(
            campaign_id=campaign.id,
            body=GitHubPublishRequest(mode="pr"),
            background_tasks=bg,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result == {"job_id": str(job.id)}


@pytest.mark.asyncio
async def test_publish_github_403_wrong_owner():
    from fastapi import BackgroundTasks
    from app.routers.publishing import publish_campaign_github, GitHubPublishRequest

    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    client = _make_client(user_id=other_user_id)
    campaign = _make_campaign(client_id=client.id, status="approved")
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await publish_campaign_github(
                campaign_id=campaign.id,
                body=GitHubPublishRequest(mode="pr"),
                background_tasks=BackgroundTasks(),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_publish_github_409_non_approved_campaign():
    from fastapi import BackgroundTasks
    from app.routers.publishing import publish_campaign_github, GitHubPublishRequest

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id, status="pending_approval")
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await publish_campaign_github(
                campaign_id=campaign.id,
                body=GitHubPublishRequest(mode="commit"),
                background_tasks=BackgroundTasks(),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 409


# ── GET /connections/github/installation-id ───────────────────────────────────

@pytest.mark.asyncio
async def test_get_existing_github_installation_id_no_connection():
    """Returns null when the user has no GitHub connections on any client."""
    from app.routers.publishing import get_existing_github_installation_id

    user_id = uuid.uuid4()
    db = AsyncMock()
    db_result = MagicMock()
    db_result.scalar_one_or_none.return_value = None
    db.execute.return_value = db_result

    result = await get_existing_github_installation_id(
        current_user={"user_id": str(user_id)},
        db=db,
    )

    assert result == {"installation_id": None}


@pytest.mark.asyncio
async def test_get_existing_github_installation_id_found():
    """Returns the installation_id when one of the user's clients has a GitHub connection."""
    from app.core.security import encrypt_credential
    from app.routers.publishing import get_existing_github_installation_id

    user_id = uuid.uuid4()
    encrypted = encrypt_credential(json.dumps({"installation_id": "12345"}))

    db = AsyncMock()
    db_result = MagicMock()
    db_result.scalar_one_or_none.return_value = encrypted
    db.execute.return_value = db_result

    result = await get_existing_github_installation_id(
        current_user={"user_id": str(user_id)},
        db=db,
    )

    assert result == {"installation_id": "12345"}


@pytest.mark.asyncio
async def test_get_existing_github_installation_id_corrupt_credential():
    """Returns null (no crash) when the credential row is corrupt/un-decryptable."""
    from app.routers.publishing import get_existing_github_installation_id

    user_id = uuid.uuid4()

    db = AsyncMock()
    db_result = MagicMock()
    db_result.scalar_one_or_none.return_value = b"not-valid-encrypted-data"
    db.execute.return_value = db_result

    result = await get_existing_github_installation_id(
        current_user={"user_id": str(user_id)},
        db=db,
    )

    assert result == {"installation_id": None}


@pytest.mark.asyncio
async def test_get_existing_github_installation_id_unauthenticated():
    """Returns 401 when called with an invalid/missing user session."""
    from app.routers.publishing import get_existing_github_installation_id

    db = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await get_existing_github_installation_id(
            current_user={},
            db=db,
        )

    assert exc_info.value.status_code == 401


# ── POST /campaigns/{id}/publish — publish_campaign_now ──────────────────────


def _make_connection(client_id=None):
    pc = MagicMock()
    pc.id = uuid.uuid4()
    pc.client_id = client_id or uuid.uuid4()
    pc.platform = "wordpress"
    return pc


@pytest.mark.asyncio
async def test_publish_campaign_now_allows_published_status():
    """POST /campaigns/{id}/publish returns 202 when campaign.status == 'published' (re-publish)."""
    from fastapi import BackgroundTasks
    from app.routers.publishing import publish_campaign_now

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id, status="published")
    conn = _make_connection(client_id=client.id)
    job = _make_job(campaign_id=campaign.id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.check_trial_not_expired", AsyncMock()),
        patch("app.routers.publishing.get_connections_for_client", AsyncMock(return_value=[conn])),
        patch("app.routers.publishing.create_job", AsyncMock(return_value=job)),
        patch("app.routers.publishing.run_publish", MagicMock()),
    ):
        bg = BackgroundTasks()
        result = await publish_campaign_now(
            campaign_id=campaign.id,
            background_tasks=bg,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result == {"job_id": str(job.id)}


@pytest.mark.asyncio
async def test_publish_campaign_now_allows_approved_status():
    """POST /campaigns/{id}/publish returns 202 when campaign.status == 'approved' (normal publish)."""
    from fastapi import BackgroundTasks
    from app.routers.publishing import publish_campaign_now

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id, status="approved")
    conn = _make_connection(client_id=client.id)
    job = _make_job(campaign_id=campaign.id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.check_trial_not_expired", AsyncMock()),
        patch("app.routers.publishing.get_connections_for_client", AsyncMock(return_value=[conn])),
        patch("app.routers.publishing.create_job", AsyncMock(return_value=job)),
        patch("app.routers.publishing.run_publish", MagicMock()),
    ):
        bg = BackgroundTasks()
        result = await publish_campaign_now(
            campaign_id=campaign.id,
            background_tasks=bg,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result == {"job_id": str(job.id)}


@pytest.mark.parametrize("invalid_status", ["pending_approval", "rejected", "failed"])
@pytest.mark.asyncio
async def test_publish_campaign_now_rejects_invalid_statuses(invalid_status):
    """POST /campaigns/{id}/publish returns 400 INVALID_STATUS_TRANSITION for non-publishable statuses."""
    from fastapi import BackgroundTasks
    from app.routers.publishing import publish_campaign_now

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id, status=invalid_status)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.check_trial_not_expired", AsyncMock()),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await publish_campaign_now(
                campaign_id=campaign.id,
                background_tasks=BackgroundTasks(),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "INVALID_STATUS_TRANSITION"


# ── POST /campaigns/{id}/publish-headless ─────────────────────────────────────


def _make_headless_article(client_id=None, article_id=None):
    """Minimal article mock returned by create_or_update_article_from_campaign."""
    a = MagicMock()
    a.id = article_id or uuid.uuid4()
    a.slug = "my-headless-article"
    a.status = "published"
    a.client_id = client_id or uuid.uuid4()
    return a


@pytest.mark.asyncio
async def test_publish_headless_approved_campaign_200():
    """POST publish-headless on an approved campaign returns 200 with article_id/slug/status
    and transitions the campaign to 'published'."""
    from app.routers.publishing import publish_headless

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id, status="approved")
    article = _make_headless_article()
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    with (
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.check_trial_not_expired", AsyncMock()),
        patch("app.routers.publishing.create_or_update_article_from_campaign", AsyncMock(return_value=article)),
    ):
        result = await publish_headless(
            campaign_id=campaign.id,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result["article_id"] == str(article.id)
    assert result["slug"] == "my-headless-article"
    assert campaign.status == "published"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_publish_headless_published_campaign_200():
    """POST publish-headless on an already-published campaign returns 200 (idempotent call)."""
    from app.routers.publishing import publish_headless

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id, status="published")
    article = _make_headless_article()
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    with (
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.check_trial_not_expired", AsyncMock()),
        patch("app.routers.publishing.create_or_update_article_from_campaign", AsyncMock(return_value=article)),
    ):
        result = await publish_headless(
            campaign_id=campaign.id,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result["article_id"] == str(article.id)
    assert result["slug"] == "my-headless-article"
    db.commit.assert_called_once()


@pytest.mark.parametrize("invalid_status", ["pending_approval", "rejected", "failed"])
@pytest.mark.asyncio
async def test_publish_headless_400_invalid_status(invalid_status):
    """POST publish-headless returns 400 INVALID_STATUS_TRANSITION for non-publishable statuses."""
    from app.routers.publishing import publish_headless

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id, status=invalid_status)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.check_trial_not_expired", AsyncMock()),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await publish_headless(
                campaign_id=campaign.id,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "INVALID_STATUS_TRANSITION"


@pytest.mark.asyncio
async def test_publish_headless_trial_expired_raises():
    """POST publish-headless propagates TRIAL_EXPIRED from check_trial_not_expired."""
    from app.routers.publishing import publish_headless

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id, status="approved")
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.check_trial_not_expired", AsyncMock(side_effect=HTTPException(
            status_code=402,
            detail={"error": {"code": "TRIAL_EXPIRED", "message": "Trial expired.", "detail": {}}},
        ))),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await publish_headless(
                campaign_id=campaign.id,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 402
    assert exc_info.value.detail["error"]["code"] == "TRIAL_EXPIRED"


@pytest.mark.asyncio
async def test_publish_headless_no_content_400():
    """POST publish-headless returns 400 NO_CONTENT when campaign has no blog content."""
    from app.routers.publishing import publish_headless

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id, status="approved")
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.check_trial_not_expired", AsyncMock()),
        patch("app.routers.publishing.create_or_update_article_from_campaign", AsyncMock(return_value=None)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await publish_headless(
                campaign_id=campaign.id,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "NO_CONTENT"


@pytest.mark.asyncio
async def test_publish_headless_404_campaign_not_found():
    """Returns 404 when the campaign doesn't exist."""
    from app.routers.publishing import publish_headless

    user_id = uuid.uuid4()
    db = AsyncMock()

    with patch("app.routers.publishing.get_campaign", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as exc_info:
            await publish_headless(
                campaign_id=uuid.uuid4(),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_publish_headless_404_wrong_owner():
    """Returns 404 when the campaign's client doesn't belong to the current user."""
    from app.routers.publishing import publish_headless

    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    client = _make_client(user_id=other_user_id)
    campaign = _make_campaign(client_id=client.id, status="approved")
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await publish_headless(
                campaign_id=campaign.id,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 404
