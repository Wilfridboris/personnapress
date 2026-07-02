"""Unit tests for services/generation.py with mocked Gemini calls."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_job(campaign_id=None, status="pending"):
    job = MagicMock()
    job.id = uuid.uuid4()
    job.campaign_id = campaign_id or uuid.uuid4()
    job.status = status
    job.started_at = None
    job.error_details = None
    return job


def _make_campaign(client_id=None):
    campaign = MagicMock()
    campaign.id = uuid.uuid4()
    campaign.client_id = client_id or uuid.uuid4()
    campaign.brain_dump = "Raw brain dump text"
    campaign.blog_html = None
    campaign.voice_score = None
    campaign.x_post = None
    campaign.linkedin_post = None
    return campaign


def _make_client(user_id=None, bvp=None):
    client = MagicMock()
    client.id = uuid.uuid4()
    client.user_id = user_id or uuid.uuid4()
    client.brand_voice_profile = bvp
    return client


def _make_db(job, campaign, client):
    """Return a mock AsyncSession that returns the given objects on execute."""
    db = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    async def mock_execute(stmt):
        result = MagicMock()
        # Heuristic: check the WHERE clause target type via __str__
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


_BVP = {
    "tone": ["authoritative"],
    "cadence": {"avg_sentence_length": 18, "variation_pattern": "x", "paragraph_structure": "y"},
    "banned_jargon": ["leverage"],
}

_BLOG_HTML = "<h1>Test Title</h1><p>Body text here.</p>"
_VOICE_SCORE = {"tone_score": 9, "cadence_score": 8, "jargon_violations": 0}
_SOCIAL = {"x_post": "Tweet!", "linkedin_post": "LinkedIn post " * 40}


@pytest.mark.asyncio
@patch("app.services.generation.generation_logs_repo")
@patch("app.services.generation.gemini")
async def test_happy_path_all_fields_updated(mock_gemini, mock_logs_repo):
    from app.services.generation import run_generation_pipeline

    job_id = uuid.uuid4()
    campaign = _make_campaign()
    client = _make_client(bvp=_BVP)
    job = _make_job(campaign_id=campaign.id)

    mock_gemini.generate_blog = AsyncMock(return_value=_BLOG_HTML)
    mock_gemini.check_fidelity = AsyncMock(return_value=_VOICE_SCORE)
    mock_gemini.generate_social = AsyncMock(return_value=_SOCIAL)
    mock_logs_repo.create_generation_log = AsyncMock()

    db = _make_db(job, campaign, client)

    await run_generation_pipeline(job_id, db)

    assert campaign.blog_html == _BLOG_HTML
    assert campaign.voice_score == _VOICE_SCORE
    assert campaign.x_post == "Tweet!"
    assert campaign.linkedin_post == _SOCIAL["linkedin_post"]
    # Job must still be in_progress (not complete) after text generation
    assert job.status == "in_progress"


@pytest.mark.asyncio
@patch("app.services.generation.generation_logs_repo")
@patch("app.services.generation.gemini")
async def test_no_bvp_uses_default_voice_generation_completes(mock_gemini, mock_logs_repo):
    from app.services.generation import run_generation_pipeline

    job_id = uuid.uuid4()
    campaign = _make_campaign()
    client = _make_client(bvp=None)
    job = _make_job(campaign_id=campaign.id)

    mock_gemini.generate_blog = AsyncMock(return_value=_BLOG_HTML)
    mock_gemini.check_fidelity = AsyncMock(return_value={"tone_score": 10, "cadence_score": 10, "jargon_violations": 0})
    mock_gemini.generate_social = AsyncMock(return_value=_SOCIAL)
    mock_logs_repo.create_generation_log = AsyncMock()

    db = _make_db(job, campaign, client)

    await run_generation_pipeline(job_id, db)

    assert campaign.blog_html == _BLOG_HTML
    assert job.status == "in_progress"


@pytest.mark.asyncio
@patch("app.services.generation.sentry_sdk")
@patch("app.services.generation.generation_logs_repo")
@patch("app.services.generation.gemini")
async def test_fidelity_check_invalid_json_fails_job(mock_gemini, mock_logs_repo, mock_sentry):
    from app.services.generation import run_generation_pipeline

    job_id = uuid.uuid4()
    campaign = _make_campaign()
    client = _make_client(bvp=_BVP)
    job = _make_job(campaign_id=campaign.id)

    mock_gemini.generate_blog = AsyncMock(return_value=_BLOG_HTML)
    mock_gemini.check_fidelity = AsyncMock(side_effect=ValueError("invalid JSON"))
    mock_logs_repo.create_generation_log = AsyncMock()

    db = _make_db(job, campaign, client)

    await run_generation_pipeline(job_id, db)

    assert job.status == "failed"
    assert "temporarily unavailable" in job.error_details
    mock_sentry.capture_exception.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.generation.sentry_sdk")
@patch("app.services.generation.generation_logs_repo")
@patch("app.services.generation.gemini")
async def test_blog_generation_failure_after_retries_fails_job(mock_gemini, mock_logs_repo, mock_sentry):
    from app.services.generation import run_generation_pipeline

    job_id = uuid.uuid4()
    campaign = _make_campaign()
    client = _make_client(bvp=_BVP)
    job = _make_job(campaign_id=campaign.id)

    # Simulate a non-transient error (RuntimeError) reaching the service layer
    mock_gemini.generate_blog = AsyncMock(side_effect=RuntimeError("All retries exhausted"))
    mock_logs_repo.create_generation_log = AsyncMock()

    db = _make_db(job, campaign, client)

    await run_generation_pipeline(job_id, db)

    assert job.status == "failed"
    assert "temporarily unavailable" in job.error_details
    mock_sentry.capture_exception.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.generation.generation_logs_repo")
@patch("app.services.generation.gemini")
async def test_blog_html_stored_as_is_even_if_malformed(mock_gemini, mock_logs_repo):
    from app.services.generation import run_generation_pipeline

    job_id = uuid.uuid4()
    campaign = _make_campaign()
    client = _make_client(bvp=_BVP)
    job = _make_job(campaign_id=campaign.id)

    malformed_html = "<h1>Title<p>No closing tag"
    mock_gemini.generate_blog = AsyncMock(return_value=malformed_html)
    mock_gemini.check_fidelity = AsyncMock(return_value=_VOICE_SCORE)
    mock_gemini.generate_social = AsyncMock(return_value=_SOCIAL)
    mock_logs_repo.create_generation_log = AsyncMock()

    db = _make_db(job, campaign, client)

    await run_generation_pipeline(job_id, db)

    assert campaign.blog_html == malformed_html


@pytest.mark.asyncio
@patch("app.services.generation.generation_logs_repo")
@patch("app.services.generation.gemini")
async def test_job_marked_in_progress_before_generation(mock_gemini, mock_logs_repo):
    from app.services.generation import run_generation_pipeline

    job_id = uuid.uuid4()
    campaign = _make_campaign()
    client = _make_client(bvp=_BVP)
    job = _make_job(campaign_id=campaign.id, status="pending")

    mock_gemini.generate_blog = AsyncMock(return_value=_BLOG_HTML)
    mock_gemini.check_fidelity = AsyncMock(return_value=_VOICE_SCORE)
    mock_gemini.generate_social = AsyncMock(return_value=_SOCIAL)
    mock_logs_repo.create_generation_log = AsyncMock()

    db = _make_db(job, campaign, client)
    committed_statuses = []

    original_commit = db.commit

    async def track_commit():
        committed_statuses.append(job.status)
        await original_commit()

    db.commit = AsyncMock(side_effect=track_commit)

    await run_generation_pipeline(job_id, db)

    # First commit should be the in_progress status update
    assert "in_progress" in committed_statuses
