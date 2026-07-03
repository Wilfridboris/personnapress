"""Tests for POST /api/v1/campaigns/{id}/publish/retry endpoint."""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_campaign(client_id=None, status="failed"):
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


def _make_job(job_id=None, campaign_id=None, attempt_count=0, error_details=None, status="failed"):
    j = MagicMock()
    j.id = job_id or uuid.uuid4()
    j.campaign_id = campaign_id
    j.attempt_count = attempt_count
    j.error_details = error_details or json.dumps({"wordpress": "WordPress returned 401 — check your Application Password"})
    j.status = status
    return j


async def test_retry_publish_success():
    from app.routers.publishing import retry_platform_publish

    user_id = uuid.uuid4()
    campaign = _make_campaign()
    client = _make_client(user_id=user_id, client_id=campaign.client_id)
    job = _make_job(campaign_id=campaign.id, attempt_count=0)
    db = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    background_tasks = MagicMock()
    background_tasks.add_task = MagicMock()

    with (
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_publish_job_for_campaign", AsyncMock(return_value=job)),
    ):
        from app.routers.publishing import RetryRequest
        result = await retry_platform_publish(
            campaign_id=campaign.id,
            body=RetryRequest(platform="wordpress"),
            background_tasks=background_tasks,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert "job_id" in result
    assert result["job_id"] == str(job.id)
    assert job.attempt_count == 1
    db.commit.assert_called_once()
    background_tasks.add_task.assert_called_once()


async def test_retry_wrong_campaign_status():
    from app.routers.publishing import retry_platform_publish, RetryRequest
    from fastapi import HTTPException

    user_id = uuid.uuid4()
    campaign = _make_campaign(status="published")
    client = _make_client(user_id=user_id, client_id=campaign.client_id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await retry_platform_publish(
                campaign_id=campaign.id,
                body=RetryRequest(platform="wordpress"),
                background_tasks=MagicMock(),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "INVALID_STATUS_TRANSITION"


async def test_retry_max_retries():
    from app.routers.publishing import retry_platform_publish, RetryRequest
    from fastapi import HTTPException

    user_id = uuid.uuid4()
    campaign = _make_campaign(status="failed")
    client = _make_client(user_id=user_id, client_id=campaign.client_id)
    job = _make_job(campaign_id=campaign.id, attempt_count=3)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_publish_job_for_campaign", AsyncMock(return_value=job)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await retry_platform_publish(
                campaign_id=campaign.id,
                body=RetryRequest(platform="wordpress"),
                background_tasks=MagicMock(),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "MAX_RETRIES_REACHED"


async def test_retry_ownership():
    from app.routers.publishing import retry_platform_publish, RetryRequest
    from fastapi import HTTPException

    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    campaign = _make_campaign(status="failed")
    client = _make_client(user_id=other_user_id, client_id=campaign.client_id)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await retry_platform_publish(
                campaign_id=campaign.id,
                body=RetryRequest(platform="wordpress"),
                background_tasks=MagicMock(),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 404


async def test_retry_already_published_platform():
    from app.routers.publishing import retry_platform_publish, RetryRequest
    from fastapi import HTTPException

    user_id = uuid.uuid4()
    campaign = _make_campaign(status="failed")
    client = _make_client(user_id=user_id, client_id=campaign.client_id)
    # LinkedIn succeeded, wordpress failed
    error_details = json.dumps({"linkedin": "success", "wordpress": "WordPress returned 401"})
    job = _make_job(campaign_id=campaign.id, attempt_count=0, error_details=error_details)
    db = AsyncMock()

    with (
        patch("app.routers.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.publishing.get_client", AsyncMock(return_value=client)),
        patch("app.routers.publishing.get_publish_job_for_campaign", AsyncMock(return_value=job)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await retry_platform_publish(
                campaign_id=campaign.id,
                body=RetryRequest(platform="linkedin"),
                background_tasks=MagicMock(),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "PLATFORM_ALREADY_PUBLISHED"
