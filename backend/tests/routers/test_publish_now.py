"""Tests for POST /api/v1/campaigns/{id}/publish endpoint."""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


def _make_campaign(client_id=None, status="approved"):
    c = MagicMock()
    c.id = uuid.uuid4()
    c.client_id = client_id or uuid.uuid4()
    c.status = status
    return c


def _make_client(user_id=None, client_id=None):
    cl = MagicMock()
    cl.id = client_id or uuid.uuid4()
    cl.user_id = user_id or uuid.uuid4()
    return cl


def _make_connection(platform="wordpress"):
    conn = MagicMock()
    conn.id = uuid.uuid4()
    conn.platform = platform
    return conn


def _make_job(job_id=None, campaign_id=None):
    j = MagicMock()
    j.id = job_id or uuid.uuid4()
    j.campaign_id = campaign_id
    return j


async def test_publish_now_success():
    from app.routers.publishing import publish_campaign_now

    user_id = uuid.uuid4()
    campaign = _make_campaign()
    client = _make_client(user_id=user_id, client_id=campaign.client_id)
    conn = _make_connection()
    job = _make_job(campaign_id=campaign.id)
    db = AsyncMock()
    db.commit = AsyncMock()
    background_tasks = MagicMock()
    background_tasks.add_task = MagicMock()

    with (
        patch("app.routers.publishing.check_trial_not_expired", AsyncMock(return_value=None)),
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_connections_for_client", AsyncMock(return_value=[conn])),
        patch("app.routers.publishing.create_job", AsyncMock(return_value=job)),
    ):
        result = await publish_campaign_now(
            campaign_id=campaign.id,
            background_tasks=background_tasks,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert "job_id" in result
    assert result["job_id"] == str(job.id)
    db.commit.assert_called_once()
    background_tasks.add_task.assert_called_once()


async def test_publish_now_no_connections():
    from app.routers.publishing import publish_campaign_now

    user_id = uuid.uuid4()
    campaign = _make_campaign()
    client = _make_client(user_id=user_id, client_id=campaign.client_id)
    db = AsyncMock()
    background_tasks = MagicMock()

    with (
        patch("app.routers.publishing.check_trial_not_expired", AsyncMock(return_value=None)),
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_connections_for_client", AsyncMock(return_value=[])),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await publish_campaign_now(
                campaign_id=campaign.id,
                background_tasks=background_tasks,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "NO_PLATFORM_CONNECTIONS"


async def test_publish_now_wrong_status():
    from app.routers.publishing import publish_campaign_now

    user_id = uuid.uuid4()
    campaign = _make_campaign(status="pending_approval")
    client = _make_client(user_id=user_id, client_id=campaign.client_id)
    db = AsyncMock()
    background_tasks = MagicMock()

    with (
        patch("app.routers.publishing.check_trial_not_expired", AsyncMock(return_value=None)),
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await publish_campaign_now(
                campaign_id=campaign.id,
                background_tasks=background_tasks,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "INVALID_STATUS_TRANSITION"


async def test_publish_now_ownership():
    from app.routers.publishing import publish_campaign_now

    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    campaign = _make_campaign()
    client = _make_client(user_id=other_user_id, client_id=campaign.client_id)
    db = AsyncMock()
    background_tasks = MagicMock()

    with (
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await publish_campaign_now(
                campaign_id=campaign.id,
                background_tasks=background_tasks,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 404


async def test_publish_now_with_platform_filter():
    """POST {"platforms": ["wordpress"]} passes platforms to run_publish background task."""
    from app.routers.publishing import publish_campaign_now
    from app.schemas.publishing import PublishRequest

    user_id = uuid.uuid4()
    campaign = _make_campaign()
    client = _make_client(user_id=user_id, client_id=campaign.client_id)
    conn = _make_connection()
    job = _make_job(campaign_id=campaign.id)
    db = AsyncMock()
    db.commit = AsyncMock()
    background_tasks = MagicMock()
    background_tasks.add_task = MagicMock()

    with (
        patch("app.routers.publishing.check_trial_not_expired", AsyncMock(return_value=None)),
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_connections_for_client", AsyncMock(return_value=[conn])),
        patch("app.routers.publishing.create_job", AsyncMock(return_value=job)),
    ):
        result = await publish_campaign_now(
            campaign_id=campaign.id,
            background_tasks=background_tasks,
            current_user={"user_id": str(user_id)},
            db=db,
            request=PublishRequest(platforms=["wordpress"]),
        )

    assert result["job_id"] == str(job.id)
    call_args = background_tasks.add_task.call_args
    # Third positional arg after fn, job_id, campaign_id is platforms
    assert call_args.args[3] == ["wordpress"]


async def test_publish_now_no_body_publishes_all():
    """No body (request=None) passes empty platforms list — all connections dispatched."""
    from app.routers.publishing import publish_campaign_now

    user_id = uuid.uuid4()
    campaign = _make_campaign()
    client = _make_client(user_id=user_id, client_id=campaign.client_id)
    conn = _make_connection()
    job = _make_job(campaign_id=campaign.id)
    db = AsyncMock()
    db.commit = AsyncMock()
    background_tasks = MagicMock()
    background_tasks.add_task = MagicMock()

    with (
        patch("app.routers.publishing.check_trial_not_expired", AsyncMock(return_value=None)),
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_connections_for_client", AsyncMock(return_value=[conn])),
        patch("app.routers.publishing.create_job", AsyncMock(return_value=job)),
    ):
        result = await publish_campaign_now(
            campaign_id=campaign.id,
            background_tasks=background_tasks,
            current_user={"user_id": str(user_id)},
            db=db,
            # no request — defaults to None, meaning all platforms
        )

    assert result["job_id"] == str(job.id)
    call_args = background_tasks.add_task.call_args
    assert call_args.args[3] == []


async def test_publish_now_empty_platforms_list_publishes_all():
    """{"platforms": []} is treated the same as no body — all connections dispatched."""
    from app.routers.publishing import publish_campaign_now
    from app.schemas.publishing import PublishRequest

    user_id = uuid.uuid4()
    campaign = _make_campaign()
    client = _make_client(user_id=user_id, client_id=campaign.client_id)
    conn = _make_connection()
    job = _make_job(campaign_id=campaign.id)
    db = AsyncMock()
    db.commit = AsyncMock()
    background_tasks = MagicMock()
    background_tasks.add_task = MagicMock()

    with (
        patch("app.routers.publishing.check_trial_not_expired", AsyncMock(return_value=None)),
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_connections_for_client", AsyncMock(return_value=[conn])),
        patch("app.routers.publishing.create_job", AsyncMock(return_value=job)),
    ):
        await publish_campaign_now(
            campaign_id=campaign.id,
            background_tasks=background_tasks,
            current_user={"user_id": str(user_id)},
            db=db,
            request=PublishRequest(platforms=[]),
        )

    call_args = background_tasks.add_task.call_args
    assert call_args.args[3] == []
