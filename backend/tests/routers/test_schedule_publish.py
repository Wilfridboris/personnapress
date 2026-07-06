"""Tests for schedule/cancel publish endpoints."""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


def _make_campaign(client_id=None, status="approved", scheduled_at=None):
    c = MagicMock()
    c.id = uuid.uuid4()
    c.client_id = client_id or uuid.uuid4()
    c.status = status
    c.scheduled_at = scheduled_at
    return c


def _make_client(user_id=None, client_id=None):
    cl = MagicMock()
    cl.id = client_id or uuid.uuid4()
    cl.user_id = user_id or uuid.uuid4()
    return cl


def _make_job(job_id=None, campaign_id=None):
    j = MagicMock()
    j.id = job_id or uuid.uuid4()
    j.campaign_id = campaign_id
    j.scheduled_at = None
    return j


def _future_dt() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=2)


def _past_dt() -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=1)


# ── Schedule endpoint ────────────────────────────────────────────────────────

async def test_schedule_publish_success():
    from app.routers.publishing import schedule_campaign_publish, ScheduleRequest

    user_id = uuid.uuid4()
    campaign = _make_campaign()
    client = _make_client(user_id=user_id, client_id=campaign.client_id)
    job = _make_job(campaign_id=campaign.id)
    db = AsyncMock()
    db.commit = AsyncMock()
    mock_scheduler = MagicMock()
    scheduled_at = _future_dt()

    with (
        patch("app.routers.publishing.check_trial_not_expired", AsyncMock(return_value=None)),
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.create_job", AsyncMock(return_value=job)),
        patch("app.routers.publishing.update_campaign_scheduled_at", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.scheduler", mock_scheduler),
    ):
        result = await schedule_campaign_publish(
            campaign_id=campaign.id,
            body=ScheduleRequest(scheduled_at=scheduled_at),
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert "job_id" in result
    assert "scheduled_at" in result
    db.commit.assert_called_once()
    mock_scheduler.add_job.assert_called_once()


async def test_schedule_publish_past_time():
    from app.routers.publishing import schedule_campaign_publish, ScheduleRequest

    user_id = uuid.uuid4()
    campaign = _make_campaign()
    client = _make_client(user_id=user_id, client_id=campaign.client_id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.check_trial_not_expired", AsyncMock(return_value=None)),
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await schedule_campaign_publish(
                campaign_id=campaign.id,
                body=ScheduleRequest(scheduled_at=_past_dt()),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "SCHEDULED_TIME_IN_PAST"


async def test_schedule_publish_not_approved():
    from app.routers.publishing import schedule_campaign_publish, ScheduleRequest

    user_id = uuid.uuid4()
    campaign = _make_campaign(status="pending_approval")
    client = _make_client(user_id=user_id, client_id=campaign.client_id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.check_trial_not_expired", AsyncMock(return_value=None)),
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await schedule_campaign_publish(
                campaign_id=campaign.id,
                body=ScheduleRequest(scheduled_at=_future_dt()),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "INVALID_STATUS_TRANSITION"


# ── Cancel endpoint ──────────────────────────────────────────────────────────

async def test_cancel_schedule_success():
    from app.routers.publishing import cancel_scheduled_publish

    user_id = uuid.uuid4()
    campaign = _make_campaign()
    client = _make_client(user_id=user_id, client_id=campaign.client_id)
    job = _make_job(campaign_id=campaign.id)
    db = AsyncMock()
    db.commit = AsyncMock()
    db.delete = AsyncMock()
    mock_scheduler = MagicMock()

    with (
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_scheduled_job", AsyncMock(return_value=job)),
        patch("app.routers.publishing.update_campaign_scheduled_at", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.scheduler", mock_scheduler),
    ):
        result = await cancel_scheduled_publish(
            campaign_id=campaign.id,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result["status"] == "approved"
    mock_scheduler.remove_job.assert_called_once_with(str(job.id))
    db.delete.assert_called_once_with(job)
    db.commit.assert_called_once()


async def test_cancel_schedule_not_found():
    from app.routers.publishing import cancel_scheduled_publish

    user_id = uuid.uuid4()
    campaign = _make_campaign()
    client = _make_client(user_id=user_id, client_id=campaign.client_id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_scheduled_job", AsyncMock(return_value=None)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await cancel_scheduled_publish(
                campaign_id=campaign.id,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 404
