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
