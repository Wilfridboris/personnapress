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


# ---------------------------------------------------------------------------
# Headless scheduling (AC 4, 10)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_publish_headless_immediate_no_body():
    """No body (request=None) → publishes immediately, campaign marked published."""
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
            # request=None → immediate publish path
        )

    assert result["article_id"] == str(article.id)
    assert campaign.status == "published"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_publish_headless_scheduled():
    """Body with scheduled_at → article created as hidden, APScheduler job registered."""
    from datetime import timedelta
    from app.routers.publishing import publish_headless
    from app.schemas.publishing import PublishHeadlessRequest

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id, status="approved")
    article = _make_headless_article()
    article.status = "hidden"
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    mock_scheduler = MagicMock()
    future_dt = datetime.now(timezone.utc) + timedelta(hours=1)

    with (
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.check_trial_not_expired", AsyncMock()),
        patch("app.routers.publishing.update_campaign_scheduled_at", AsyncMock()),
        patch("app.routers.publishing.create_or_update_article_from_campaign", AsyncMock(return_value=article)),
        patch("app.routers.publishing.scheduler", mock_scheduler),
    ):
        result = await publish_headless(
            campaign_id=campaign.id,
            current_user={"user_id": str(user_id)},
            db=db,
            request=PublishHeadlessRequest(scheduled_at=future_dt),
        )

    assert result["status"] == "scheduled"
    assert result["article_id"] == str(article.id)
    # Campaign must NOT be marked published yet
    assert campaign.status != "published"
    # APScheduler add_job must be called with headless job id — and BEFORE db.commit
    mock_scheduler.add_job.assert_called_once()
    call_kwargs = mock_scheduler.add_job.call_args[1]
    assert call_kwargs["id"] == f"headless_{campaign.id}"
    assert str(campaign.id) in call_kwargs["args"]
    assert call_kwargs["misfire_grace_time"] == 3600


@pytest.mark.asyncio
async def test_publish_headless_schedule_replace_existing():
    """Scheduling headless twice uses replace_existing=True — no duplicate job."""
    from datetime import timedelta
    from app.routers.publishing import publish_headless
    from app.schemas.publishing import PublishHeadlessRequest

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id, status="approved")
    article = _make_headless_article()
    article.status = "hidden"
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    mock_scheduler = MagicMock()
    future_dt = datetime.now(timezone.utc) + timedelta(hours=2)

    with (
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.check_trial_not_expired", AsyncMock()),
        patch("app.routers.publishing.update_campaign_scheduled_at", AsyncMock()),
        patch("app.routers.publishing.create_or_update_article_from_campaign", AsyncMock(return_value=article)),
        patch("app.routers.publishing.scheduler", mock_scheduler),
    ):
        for _ in range(2):
            await publish_headless(
                campaign_id=campaign.id,
                current_user={"user_id": str(user_id)},
                db=db,
                request=PublishHeadlessRequest(scheduled_at=future_dt),
            )

    assert mock_scheduler.add_job.call_count == 2
    for call in mock_scheduler.add_job.call_args_list:
        assert call[1]["replace_existing"] is True


# ---------------------------------------------------------------------------
# run_publish_headless worker (AC 10)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_publish_headless_flips_status():
    """Given article with status='hidden', run_publish_headless sets it to 'published'."""
    from app.workers.publish import run_publish_headless

    campaign_id = uuid.uuid4()
    article = MagicMock()
    article.id = uuid.uuid4()
    article.status = "hidden"

    db_mock = AsyncMock()
    db_mock.commit = AsyncMock()

    async def fake_get_article_by_campaign_id(db, cid):
        return article

    with (
        patch("app.workers.publish.get_article_by_campaign_id", side_effect=fake_get_article_by_campaign_id),
        patch("app.workers.publish.get_session_context") as mock_ctx,
    ):
        mock_ctx.return_value.__aenter__ = AsyncMock(return_value=db_mock)
        mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

        await run_publish_headless(str(campaign_id))

    assert article.status == "published"
    assert article.published_at is not None
    db_mock.commit.assert_called_once()


@pytest.mark.asyncio
async def test_run_publish_headless_missing_article():
    """If no article exists for campaign, logs warning and returns without error."""
    from app.workers.publish import run_publish_headless
    import logging

    campaign_id = uuid.uuid4()
    db_mock = AsyncMock()
    db_mock.commit = AsyncMock()

    with (
        patch("app.workers.publish.get_article_by_campaign_id", AsyncMock(return_value=None)),
        patch("app.workers.publish.get_session_context") as mock_ctx,
    ):
        mock_ctx.return_value.__aenter__ = AsyncMock(return_value=db_mock)
        mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

        # Should not raise
        await run_publish_headless(str(campaign_id))

    db_mock.commit.assert_not_called()


# ---------------------------------------------------------------------------
# LinkedIn target endpoints (AC 9, story 5.7)
# ---------------------------------------------------------------------------

def _make_linkedin_connection(client_id=None, creds=None):
    from app.core.security import encrypt_credential
    pc = MagicMock()
    pc.id = uuid.uuid4()
    pc.client_id = client_id or uuid.uuid4()
    pc.platform = "linkedin"
    if creds is None:
        creds = {"access_token": "li_tok", "name": "Test User"}
    pc.encrypted_credentials = encrypt_credential(json.dumps(creds))
    return pc


@pytest.mark.asyncio
async def test_update_linkedin_target_stores_org():
    """PATCH /connections/linkedin/target with organization payload persists org fields."""
    from app.routers.publishing import update_linkedin_target, LinkedInTargetPatchRequest
    from app.core.security import decrypt_credential

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    li_conn = _make_linkedin_connection(client_id=client.id)
    stored_creds = []

    async def fake_upsert(db, client_id, platform, encrypted):
        stored_creds.append(json.loads(decrypt_credential(encrypted)))

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_connections_for_client", AsyncMock(return_value=[li_conn])),
        patch("app.routers.publishing.upsert_connection", fake_upsert),
    ):
        result = await update_linkedin_target(
            client_id=client.id,
            body=LinkedInTargetPatchRequest(target="organization", org_id="123456", org_name="Acme Corp"),
            current_user={"user_id": str(user_id)},
            db=AsyncMock(),
        )

    assert result["target"] == "organization"
    assert result["org_id"] == "123456"
    assert result["org_name"] == "Acme Corp"
    assert len(stored_creds) == 1
    assert stored_creds[0]["target"] == "organization"
    assert stored_creds[0]["org_id"] == "123456"
    assert stored_creds[0]["org_name"] == "Acme Corp"


@pytest.mark.asyncio
async def test_update_linkedin_target_org_missing_org_id_returns_422():
    """PATCH /connections/linkedin/target with target=organization and no org_id raises HTTP 422."""
    from app.routers.publishing import update_linkedin_target, LinkedInTargetPatchRequest
    from fastapi import HTTPException

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    li_conn = _make_linkedin_connection(client_id=client.id)

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_connections_for_client", AsyncMock(return_value=[li_conn])),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await update_linkedin_target(
                client_id=client.id,
                body=LinkedInTargetPatchRequest(target="organization"),
                current_user={"user_id": str(user_id)},
                db=AsyncMock(),
            )

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_list_linkedin_organizations_disabled_returns_403():
    """GET /connections/linkedin/organizations returns 403 when LINKEDIN_ORG_POSTING_ENABLED=false."""
    from app.routers.publishing import list_linkedin_organizations
    from fastapi import HTTPException
    from app.core.config import settings

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)

    original = settings.LINKEDIN_ORG_POSTING_ENABLED
    try:
        settings.LINKEDIN_ORG_POSTING_ENABLED = False

        with (
            patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
            patch("app.routers.publishing.get_connections_for_client", AsyncMock(return_value=[])),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await list_linkedin_organizations(
                    client_id=client.id,
                    current_user={"user_id": str(user_id)},
                    db=AsyncMock(),
                )

        assert exc_info.value.status_code == 403
    finally:
        settings.LINKEDIN_ORG_POSTING_ENABLED = original


@pytest.mark.asyncio
async def test_list_linkedin_organizations_two_step_resolution():
    """org listing uses two calls: ACLs for URNs, then /rest/organizations/{id} for names."""
    from app.routers.publishing import list_linkedin_organizations
    from app.core.config import settings

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    creds = {"access_token": "tok", "name": "Alice", "scopes": "r_organization_admin,w_organization_social"}
    li_conn = _make_linkedin_connection(client_id=client.id, creds=creds)

    acl_response = MagicMock()
    acl_response.status_code = 200
    acl_response.json.return_value = {"elements": [{"organization": "urn:li:organization:99999"}], "paging": {}}

    org_response = MagicMock()
    org_response.status_code = 200
    org_response.json.return_value = {"localizedName": "Acme Corp", "followersCount": 500}

    mock_http = AsyncMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_http.get = AsyncMock(side_effect=[acl_response, org_response])

    original = settings.LINKEDIN_ORG_POSTING_ENABLED
    try:
        settings.LINKEDIN_ORG_POSTING_ENABLED = True
        with (
            patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
            patch("app.routers.publishing.get_connections_for_client", AsyncMock(return_value=[li_conn])),
            patch("app.routers.publishing.httpx.AsyncClient", return_value=mock_http),
        ):
            result = await list_linkedin_organizations(
                client_id=client.id,
                current_user={"user_id": str(user_id)},
                db=AsyncMock(),
            )
    finally:
        settings.LINKEDIN_ORG_POSTING_ENABLED = original

    assert result == {"organizations": [{"id": "99999", "name": "Acme Corp", "follower_count": 500}]}


# ---------------------------------------------------------------------------
# Story 5.8: scopes persistence + linkedin_org_capable (AC 2, 4)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_linkedin_oauth_callback_persists_scopes():
    """linkedin_oauth_callback stores the scopes string from the token endpoint in the credential blob."""
    from app.routers.publishing import linkedin_oauth_callback, OAuthCallbackRequest
    from app.core.security import decrypt_credential

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    stored_creds = []

    async def fake_upsert(db, client_id, platform, encrypted):
        stored_creds.append(json.loads(decrypt_credential(encrypted)))

    scope_str = "openid,profile,w_member_social,r_organization_admin,w_organization_social"
    token_data = {"access_token": "AQX_tok", "scope": scope_str}

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_connection", AsyncMock(return_value=None)),
        patch("app.routers.publishing.linkedin_integration.exchange_code_for_token", AsyncMock(return_value=token_data)),
        patch("app.routers.publishing.linkedin_integration.get_user_name", AsyncMock(return_value="Test User")),
        patch("app.routers.publishing.upsert_connection", fake_upsert),
    ):
        result = await linkedin_oauth_callback(
            client_id=client.id,
            body=OAuthCallbackRequest(code="auth_code"),
            current_user={"user_id": str(user_id)},
            db=AsyncMock(),
        )

    assert result["connected"] is True
    assert len(stored_creds) == 1
    blob = stored_creds[0]
    assert blob["access_token"] == "AQX_tok"
    assert blob["scopes"] == scope_str
    assert "w_organization_social" in blob["scopes"]


@pytest.mark.asyncio
async def test_linkedin_oauth_callback_preserves_target_on_reconnect():
    """Reconnect via hint must not reset a previously saved linkedin_target to personal."""
    from app.routers.publishing import linkedin_oauth_callback, OAuthCallbackRequest
    from app.core.security import decrypt_credential, encrypt_credential

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    stored_creds = []

    async def fake_upsert(db, client_id, platform, encrypted):
        stored_creds.append(json.loads(decrypt_credential(encrypted)))

    existing_blob = {"access_token": "old_tok", "name": "Old Name", "target": "organization", "org_id": "urn:li:organization:999", "org_name": "Acme Corp"}
    from unittest.mock import MagicMock
    existing_conn = MagicMock()
    existing_conn.encrypted_credentials = encrypt_credential(json.dumps(existing_blob))

    scope_str = "openid,profile,w_member_social,r_organization_admin,w_organization_social"
    token_data = {"access_token": "new_tok", "scope": scope_str}

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_connection", AsyncMock(return_value=existing_conn)),
        patch("app.routers.publishing.linkedin_integration.exchange_code_for_token", AsyncMock(return_value=token_data)),
        patch("app.routers.publishing.linkedin_integration.get_user_name", AsyncMock(return_value="New Name")),
        patch("app.routers.publishing.upsert_connection", fake_upsert),
    ):
        result = await linkedin_oauth_callback(
            client_id=client.id,
            body=OAuthCallbackRequest(code="auth_code"),
            current_user={"user_id": str(user_id)},
            db=AsyncMock(),
        )

    assert result["connected"] is True
    blob = stored_creds[0]
    assert blob["access_token"] == "new_tok"
    assert blob["scopes"] == scope_str
    assert blob["target"] == "organization"
    assert blob["org_id"] == "urn:li:organization:999"
    assert blob["org_name"] == "Acme Corp"


@pytest.mark.asyncio
async def test_connections_list_linkedin_org_capable_true_for_org_scoped_blob():
    """Connections list returns linkedin_org_capable=True when blob has w_organization_social in scopes."""
    from app.routers.publishing import list_platform_connections
    from app.core.security import encrypt_credential

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)

    creds = {"access_token": "tok", "name": "Alice", "scopes": "openid,profile,w_member_social,r_organization_admin,w_organization_social"}
    li_conn = _make_linkedin_connection(client_id=client.id, creds=creds)

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_connections_for_client", AsyncMock(return_value=[li_conn])),
    ):
        response = await list_platform_connections(
            client_id=client.id,
            current_user={"user_id": str(user_id)},
            db=AsyncMock(),
        )

    li_item = next(i for i in response["items"] if i["platform"] == "linkedin")
    assert li_item["linkedin_org_capable"] is True
    # Confirm secrets are not leaked
    assert "access_token" not in li_item
    assert "scopes" not in li_item


@pytest.mark.asyncio
async def test_connections_list_linkedin_org_capable_false_for_legacy_blob():
    """Connections list returns linkedin_org_capable=False for a legacy blob with no scopes key."""
    from app.routers.publishing import list_platform_connections

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)

    # Legacy blob: no 'scopes' key (pre-5.8 connection)
    creds = {"access_token": "tok", "name": "Bob"}
    li_conn = _make_linkedin_connection(client_id=client.id, creds=creds)

    with (
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_connections_for_client", AsyncMock(return_value=[li_conn])),
    ):
        response = await list_platform_connections(
            client_id=client.id,
            current_user={"user_id": str(user_id)},
            db=AsyncMock(),
        )

    li_item = next(i for i in response["items"] if i["platform"] == "linkedin")
    assert li_item["linkedin_org_capable"] is False
