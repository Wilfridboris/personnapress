"""Unit tests for services/image.py with mocked Replicate and Supabase calls."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_job(campaign_id=None, status="in_progress"):
    job = MagicMock()
    job.id = uuid.uuid4()
    job.campaign_id = campaign_id or uuid.uuid4()
    job.status = status
    job.error_details = None
    job.completed_at = None
    return job


def _make_campaign(client_id=None, image_regen_count=0):
    campaign = MagicMock()
    campaign.id = uuid.uuid4()
    campaign.client_id = client_id or uuid.uuid4()
    campaign.blog_html = "<h1>Test Blog Title</h1><p>Body text.</p>"
    campaign.image_url = None
    campaign.image_regen_count = image_regen_count
    return campaign


def _make_client(user_id=None, bvp=None):
    client = MagicMock()
    client.id = uuid.uuid4()
    client.user_id = user_id or uuid.uuid4()
    client.brand_voice_profile = bvp
    return client


def _make_db(job, campaign, client):
    db = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    async def mock_execute(stmt):
        result = MagicMock()
        stmt_str = str(stmt)
        if "jobs" in stmt_str:
            result.scalar_one_or_none = MagicMock(return_value=job)
        elif "campaigns" in stmt_str:
            result.scalar_one_or_none = MagicMock(return_value=campaign)
        elif "clients" in stmt_str:
            result.scalar_one_or_none = MagicMock(return_value=client)
        else:
            result.scalar_one_or_none = MagicMock(return_value=None)
        return result

    db.execute = AsyncMock(side_effect=mock_execute)
    return db


# ── run_image_generation tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.services.image.generation_logs_repo")
@patch("app.services.image.supabase_storage")
@patch("app.services.image.subscription_service")
@patch("app.services.image.replicate_integration")
async def test_happy_path_image_url_set_job_complete(
    mock_replicate, mock_sub_svc, mock_storage, mock_logs
):
    """Happy path: Replicate succeeds → image_url set, job complete, log created."""
    from app.services.image import run_image_generation

    campaign_id = uuid.uuid4()
    job_id = uuid.uuid4()
    campaign = _make_campaign()
    campaign.id = campaign_id
    job = _make_job(campaign_id=campaign_id)
    job.id = job_id
    client = _make_client()

    db = _make_db(job, campaign, client)

    mock_sub_svc.check_image_limit = AsyncMock()
    mock_replicate.generate_image = AsyncMock(return_value="https://replicate.delivery/image.png")
    mock_storage.upload_image_from_url = AsyncMock(return_value="https://supabase.co/storage/v1/object/public/generated-images/test/featured.png")
    mock_logs.create_generation_log = AsyncMock()

    await run_image_generation(campaign_id, job_id, db)

    assert campaign.image_url == "https://supabase.co/storage/v1/object/public/generated-images/test/featured.png"
    assert job.status == "complete"
    assert job.completed_at is not None
    mock_logs.create_generation_log.assert_called_once()
    # replicate_count=1 in the log call
    call_kwargs = mock_logs.create_generation_log.call_args.kwargs
    assert call_kwargs["replicate_count"] == 1


@pytest.mark.asyncio
@patch("app.services.image.supabase_storage")
@patch("app.services.image.subscription_service")
@patch("app.services.image.replicate_integration")
async def test_image_limit_reached_job_complete_image_url_null(
    mock_replicate, mock_sub_svc, mock_storage
):
    """Image limit reached → job set complete, image_url remains null."""
    from app.services.image import run_image_generation

    campaign_id = uuid.uuid4()
    job_id = uuid.uuid4()
    campaign = _make_campaign()
    campaign.id = campaign_id
    job = _make_job(campaign_id=campaign_id)
    client = _make_client()
    db = _make_db(job, campaign, client)

    mock_sub_svc.check_image_limit = AsyncMock(
        side_effect=HTTPException(
            status_code=400,
            detail={"error": {"code": "IMAGE_LIMIT_EXCEEDED", "message": "limit", "detail": {}}},
        )
    )

    await run_image_generation(campaign_id, job_id, db)

    assert campaign.image_url is None
    assert job.status == "complete"
    mock_replicate.generate_image.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.image.generation_logs_repo")
@patch("app.services.image.supabase_storage")
@patch("app.services.image.subscription_service")
@patch("app.services.image.replicate_integration")
async def test_replicate_fails_after_retries_job_complete_with_error_details(
    mock_replicate, mock_sub_svc, mock_storage, mock_logs
):
    """Replicate fails after 3 retries → job complete with error_details, campaign proceeds."""
    from app.services.image import run_image_generation

    campaign_id = uuid.uuid4()
    job_id = uuid.uuid4()
    campaign = _make_campaign()
    campaign.id = campaign_id
    job = _make_job(campaign_id=campaign_id)
    client = _make_client()
    db = _make_db(job, campaign, client)

    mock_sub_svc.check_image_limit = AsyncMock()
    mock_replicate.generate_image = AsyncMock(side_effect=RuntimeError("Replicate API error"))

    with patch("app.services.image.asyncio.sleep", new=AsyncMock()):
        await run_image_generation(campaign_id, job_id, db)

    assert campaign.image_url is None
    assert job.status == "complete"
    assert "Image generation failed" in (job.error_details or "")
    mock_storage.upload_image_from_url.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.image.supabase_storage")
@patch("app.services.image.subscription_service")
@patch("app.services.image.replicate_integration")
async def test_regenerate_within_limit_returns_new_url(
    mock_replicate, mock_sub_svc, mock_storage
):
    """Regenerate: within limit → new image_url returned, regen_count incremented."""
    from app.services.image import regenerate_image

    campaign_id = uuid.uuid4()
    user_id = uuid.uuid4()
    campaign = _make_campaign(image_regen_count=1)
    campaign.id = campaign_id
    job = _make_job()
    client = _make_client()
    db = _make_db(job, campaign, client)

    mock_sub_svc.check_image_limit = AsyncMock()
    mock_replicate.generate_image = AsyncMock(return_value="https://replicate.delivery/new.png")
    mock_storage.upload_image_from_url = AsyncMock(return_value="https://supabase.co/new.png")

    url, count = await regenerate_image(campaign_id, user_id, db)

    assert url == "https://supabase.co/new.png"
    assert count == 2
    assert campaign.image_url == "https://supabase.co/new.png"
    assert campaign.image_regen_count == 2


@pytest.mark.asyncio
@patch("app.services.image.subscription_service")
@patch("app.services.image.replicate_integration")
async def test_regenerate_at_limit_raises_400(mock_replicate, mock_sub_svc):
    """Regenerate: at limit (count=3) → 400 IMAGE_REGEN_LIMIT_REACHED."""
    from app.services.image import regenerate_image

    campaign_id = uuid.uuid4()
    user_id = uuid.uuid4()
    campaign = _make_campaign(image_regen_count=3)
    campaign.id = campaign_id
    job = _make_job()
    client = _make_client()
    db = _make_db(job, campaign, client)

    mock_sub_svc.check_image_limit = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await regenerate_image(campaign_id, user_id, db)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "IMAGE_REGEN_LIMIT_REACHED"
    mock_replicate.generate_image.assert_not_called()
