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


def _make_campaign(client_id=None, target_keyword=None, target_audience=None):
    campaign = MagicMock()
    campaign.id = uuid.uuid4()
    campaign.client_id = client_id or uuid.uuid4()
    campaign.brain_dump = "Raw brain dump text"
    campaign.blog_html = None
    campaign.voice_score = None
    campaign.x_post = None
    campaign.linkedin_post = None
    campaign.target_keyword = target_keyword
    campaign.target_audience = target_audience
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
_VOICE_SCORE = {
    "tone_score": 9,
    "cadence_score": 8,
    "jargon_violations": 0,
    "seo_bluf_present": True,
    "seo_h2_count": 3,
    "seo_faq_present": True,
    "seo_fluff_detected": False,
}
_SOCIAL = {"x_post": "Tweet!", "linkedin_post": "LinkedIn post " * 40}


@pytest.mark.asyncio
@patch("app.services.generation.generation_logs_repo")
@patch("app.services.generation._llm")
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
@patch("app.services.generation._llm")
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
@patch("app.services.generation._llm")
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
@patch("app.services.generation._llm")
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
@patch("app.services.generation._llm")
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
@patch("app.services.generation._llm")
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


@pytest.mark.asyncio
@patch("app.services.generation.generation_logs_repo")
@patch("app.services.generation._llm")
async def test_target_keyword_and_audience_passed_to_generate_blog(mock_gemini, mock_logs_repo):
    """Verify target_keyword and target_audience flow from campaign → generate_blog call."""
    from app.services.generation import run_generation_pipeline

    job_id = uuid.uuid4()
    campaign = _make_campaign(target_keyword="indie app founders", target_audience="solo iOS developers")
    client = _make_client(bvp=_BVP)
    job = _make_job(campaign_id=campaign.id)

    mock_gemini.generate_blog = AsyncMock(return_value=_BLOG_HTML)
    mock_gemini.check_fidelity = AsyncMock(return_value=_VOICE_SCORE)
    mock_gemini.generate_social = AsyncMock(return_value=_SOCIAL)
    mock_logs_repo.create_generation_log = AsyncMock()

    db = _make_db(job, campaign, client)
    await run_generation_pipeline(job_id, db)

    call_args = mock_gemini.generate_blog.call_args
    positional = call_args[0]
    # generate_blog is called as fn(*args) via _gemini_with_retry
    # args: brain_dump, brand_voice_profile, thinking_tokens, target_keyword, target_audience
    assert positional[3] == "indie app founders"
    assert positional[4] == "solo iOS developers"


@pytest.mark.asyncio
@patch("app.services.generation.generation_logs_repo")
@patch("app.services.generation._llm")
async def test_null_keyword_and_audience_still_produces_blog(mock_gemini, mock_logs_repo):
    """Regression: when target_keyword and target_audience are None, pipeline succeeds."""
    from app.services.generation import run_generation_pipeline

    job_id = uuid.uuid4()
    campaign = _make_campaign(target_keyword=None, target_audience=None)
    client = _make_client(bvp=_BVP)
    job = _make_job(campaign_id=campaign.id)

    mock_gemini.generate_blog = AsyncMock(return_value=_BLOG_HTML)
    mock_gemini.check_fidelity = AsyncMock(return_value=_VOICE_SCORE)
    mock_gemini.generate_social = AsyncMock(return_value=_SOCIAL)
    mock_logs_repo.create_generation_log = AsyncMock()

    db = _make_db(job, campaign, client)
    await run_generation_pipeline(job_id, db)

    assert campaign.blog_html == _BLOG_HTML
    call_args = mock_gemini.generate_blog.call_args
    positional = call_args[0]
    assert positional[3] is None
    assert positional[4] is None


@pytest.mark.asyncio
@patch("app.services.generation.generation_logs_repo")
@patch("app.services.generation._llm")
async def test_run_generation_pipeline_sets_excerpt_and_meta(mock_llm, mock_logs_repo):
    """After generation, campaign.excerpt and campaign.meta_description are populated."""
    from app.services.generation import run_generation_pipeline

    job_id = uuid.uuid4()
    campaign = _make_campaign()
    client = _make_client(bvp=_BVP)
    job = _make_job(campaign_id=campaign.id)

    blog_with_comments = (
        "<h1>Test Title</h1>"
        "<!-- excerpt: Great hook for the article. -->"
        "<!-- meta: SEO meta description here. -->"
        "<p>Body text here.</p>"
    )
    mock_llm.generate_blog = AsyncMock(return_value=blog_with_comments)
    mock_llm.check_fidelity = AsyncMock(return_value=_VOICE_SCORE)
    mock_llm.generate_social = AsyncMock(return_value=_SOCIAL)
    mock_logs_repo.create_generation_log = AsyncMock()

    db = _make_db(job, campaign, client)
    await run_generation_pipeline(job_id, db)

    assert campaign.excerpt == "Great hook for the article."
    assert campaign.meta_description == "SEO meta description here."


# ── generate_social_only (Plan My Week path) ──────────────────────────────────

def _make_campaign_for_social(client_id=None):
    campaign = MagicMock()
    campaign.id = uuid.uuid4()
    campaign.client_id = client_id or uuid.uuid4()
    campaign.brain_dump = "Social-only brain dump"
    campaign.x_post = None
    campaign.linkedin_post = None
    campaign.updated_at = None
    return campaign


def _make_db_for_social(campaign):
    db = MagicMock()
    db.commit = AsyncMock()

    async def mock_execute(stmt):
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=campaign)
        return result

    db.execute = AsyncMock(side_effect=mock_execute)
    return db


@pytest.mark.asyncio
@patch("app.services.generation._llm")
async def test_generate_social_only_x_platform_writes_x_post(mock_llm):
    """generate_social_only calls generate_social_standalone and writes x_post."""
    from app.services.generation import generate_social_only

    campaign = _make_campaign_for_social()
    db = _make_db_for_social(campaign)

    mock_llm.generate_social_standalone = AsyncMock(
        return_value={"x_post": "Great X post!", "linkedin_post": "LinkedIn post " * 55}
    )

    await generate_social_only("brain dump", _BVP, "x", campaign.id, db)

    mock_llm.generate_social_standalone.assert_called_once()
    assert campaign.x_post == "Great X post!"
    assert campaign.linkedin_post is None
    db.commit.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.generation._llm")
async def test_generate_social_only_linkedin_platform_writes_linkedin_post(mock_llm):
    """generate_social_only calls generate_social_standalone and writes linkedin_post."""
    from app.services.generation import generate_social_only

    campaign = _make_campaign_for_social()
    db = _make_db_for_social(campaign)

    linkedin_text = "LinkedIn standalone post. " * 55
    mock_llm.generate_social_standalone = AsyncMock(
        return_value={"x_post": "Some X post.", "linkedin_post": linkedin_text}
    )

    await generate_social_only("brain dump", _BVP, "linkedin", campaign.id, db)

    mock_llm.generate_social_standalone.assert_called_once()
    assert campaign.linkedin_post == linkedin_text
    assert campaign.x_post is None
    db.commit.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.generation._llm")
async def test_generate_social_only_does_not_call_generate_social(mock_llm):
    """generate_social_only must NOT call the old generate_social function."""
    from app.services.generation import generate_social_only

    campaign = _make_campaign_for_social()
    db = _make_db_for_social(campaign)

    mock_llm.generate_social_standalone = AsyncMock(
        return_value={"x_post": "Tweet!", "linkedin_post": "LinkedIn post " * 55}
    )
    mock_llm.generate_social = AsyncMock(
        return_value={"x_post": "Should not be called", "linkedin_post": ""}
    )

    await generate_social_only("brain dump", _BVP, "x", campaign.id, db)

    mock_llm.generate_social.assert_not_called()
    mock_llm.generate_social_standalone.assert_called_once()


# ── run_social_only_pipeline (brain-dump social-only mode) ────────────────────

def _make_db_social_only(job, campaign, client):
    """Mock AsyncSession for run_social_only_pipeline (3-entity lookup sequence)."""
    db = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()

    call_count = {"n": 0}

    async def mock_execute(stmt):
        result = MagicMock()
        n = call_count["n"]
        call_count["n"] += 1
        if n == 0:
            result.scalar_one_or_none = MagicMock(return_value=job)
        elif n == 1:
            result.scalar_one_or_none = MagicMock(return_value=campaign)
        else:
            result.scalar_one_or_none = MagicMock(return_value=client)
        return result

    db.execute = AsyncMock(side_effect=mock_execute)
    return db


@pytest.mark.asyncio
@patch("app.services.generation._llm")
async def test_run_social_only_pipeline_success(mock_llm):
    """Happy path: both posts written, job marked complete, no image step."""
    from app.services.generation import run_social_only_pipeline

    job = _make_job()
    campaign = _make_campaign()
    client = _make_client(bvp=_BVP)
    db = _make_db_social_only(job, campaign, client)

    mock_llm.generate_social_standalone = AsyncMock(
        return_value={"x_post": "Tweet!", "linkedin_post": "LinkedIn post " * 40}
    )

    await run_social_only_pipeline(job.id, db)

    assert campaign.x_post == "Tweet!"
    assert campaign.linkedin_post == "LinkedIn post " * 40
    assert job.status == "in_progress"
    mock_llm.generate_social_standalone.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.generation.sentry_sdk")
@patch("app.services.generation._llm")
async def test_run_social_only_pipeline_empty_x_post(mock_llm, mock_sentry):
    """Empty x_post from LLM fails the job with the social-only error message."""
    from app.services.generation import run_social_only_pipeline

    job = _make_job()
    campaign = _make_campaign()
    client = _make_client(bvp=_BVP)
    db = _make_db_social_only(job, campaign, client)

    mock_llm.generate_social_standalone = AsyncMock(
        return_value={"x_post": "", "linkedin_post": "LinkedIn post " * 40}
    )

    await run_social_only_pipeline(job.id, db)

    assert job.status == "failed"
    assert "Social post generation failed" in job.error_details
    mock_sentry.capture_exception.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.generation.sentry_sdk")
@patch("app.services.generation._llm")
async def test_run_social_only_pipeline_empty_linkedin_post(mock_llm, mock_sentry):
    """Empty linkedin_post from LLM fails the job."""
    from app.services.generation import run_social_only_pipeline

    job = _make_job()
    campaign = _make_campaign()
    client = _make_client(bvp=_BVP)
    db = _make_db_social_only(job, campaign, client)

    mock_llm.generate_social_standalone = AsyncMock(
        return_value={"x_post": "Tweet!", "linkedin_post": ""}
    )

    await run_social_only_pipeline(job.id, db)

    assert job.status == "failed"
    assert "Social post generation failed" in job.error_details
    mock_sentry.capture_exception.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.generation._llm")
async def test_run_social_only_pipeline_leaves_job_in_progress(mock_llm):
    """run_social_only_pipeline leaves job in_progress so worker can gate image generation."""
    from app.services.generation import run_social_only_pipeline

    job = _make_job()
    campaign = _make_campaign()
    client = _make_client(bvp=_BVP)
    db = _make_db_social_only(job, campaign, client)

    mock_llm.generate_social_standalone = AsyncMock(
        return_value={"x_post": "x", "linkedin_post": "li"}
    )

    await run_social_only_pipeline(job.id, db)

    assert job.status == "in_progress"


# ── run_generation worker skip_image gate (Story 3-21) ───────────────────────

def _make_worker_job(job_id=None, campaign_id=None, status="pending"):
    j = MagicMock()
    j.id = job_id or uuid.uuid4()
    j.campaign_id = campaign_id or uuid.uuid4()
    j.status = status
    j.completed_at = None
    return j


def _make_worker_campaign(skip_image=False, campaign_type="blog_full"):
    c = MagicMock()
    c.campaign_type = campaign_type
    c.skip_image = skip_image
    return c


@pytest.mark.asyncio
async def test_worker_skips_image_when_flag_set():
    """When skip_image=True, image generation is not called and job is marked complete."""
    import uuid as _uuid
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.workers.generate import run_generation

    job_id = _uuid.uuid4()
    campaign_id = _uuid.uuid4()

    pending_job = _make_worker_job(job_id=job_id, campaign_id=campaign_id, status="pending")
    in_progress_job = _make_worker_job(job_id=job_id, campaign_id=campaign_id, status="in_progress")
    campaign = _make_worker_campaign(skip_image=True)

    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=None)

    get_job_calls = {"n": 0}

    async def mock_get_job(db, jid):
        n = get_job_calls["n"]
        get_job_calls["n"] += 1
        return pending_job if n == 0 else in_progress_job

    with (
        patch("app.workers.generate.AsyncSessionLocal", return_value=mock_db),
        patch("app.workers.generate.get_job", side_effect=mock_get_job),
        patch("app.workers.generate.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.workers.generate.generation_service.run_generation_pipeline", AsyncMock()),
        patch("app.workers.generate.image_service.run_image_generation", AsyncMock()) as mock_image,
    ):
        await run_generation(job_id)

    mock_image.assert_not_called()
    assert in_progress_job.status == "complete"
    assert in_progress_job.completed_at is not None


@pytest.mark.asyncio
async def test_worker_runs_image_when_flag_false():
    """When skip_image=False, image generation is called normally."""
    import uuid as _uuid
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.workers.generate import run_generation

    job_id = _uuid.uuid4()
    campaign_id = _uuid.uuid4()

    pending_job = _make_worker_job(job_id=job_id, campaign_id=campaign_id, status="pending")
    in_progress_job = _make_worker_job(job_id=job_id, campaign_id=campaign_id, status="in_progress")
    campaign = _make_worker_campaign(skip_image=False)

    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=None)

    get_job_calls = {"n": 0}

    async def mock_get_job(db, jid):
        n = get_job_calls["n"]
        get_job_calls["n"] += 1
        return pending_job if n == 0 else in_progress_job

    with (
        patch("app.workers.generate.AsyncSessionLocal", return_value=mock_db),
        patch("app.workers.generate.get_job", side_effect=mock_get_job),
        patch("app.workers.generate.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.workers.generate.generation_service.run_generation_pipeline", AsyncMock()),
        patch("app.workers.generate.image_service.run_image_generation", AsyncMock()) as mock_image,
    ):
        await run_generation(job_id)

    mock_image.assert_called_once_with(campaign_id, job_id, mock_db)


@pytest.mark.asyncio
async def test_run_generation_social_only_skip_image_false_calls_image_generation():
    """social_only + skip_image=False: image_service.run_image_generation is called."""
    import uuid as _uuid

    from app.workers.generate import run_generation

    job_id = _uuid.uuid4()
    campaign_id = _uuid.uuid4()

    pending_job = _make_worker_job(job_id=job_id, campaign_id=campaign_id, status="pending")
    in_progress_job = _make_worker_job(job_id=job_id, campaign_id=campaign_id, status="in_progress")
    campaign = _make_worker_campaign(skip_image=False, campaign_type="social_only")

    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=None)

    get_job_calls = {"n": 0}

    async def mock_get_job(db, jid):
        n = get_job_calls["n"]
        get_job_calls["n"] += 1
        return pending_job if n == 0 else in_progress_job

    with (
        patch("app.workers.generate.AsyncSessionLocal", return_value=mock_db),
        patch("app.workers.generate.get_job", side_effect=mock_get_job),
        patch("app.workers.generate.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.workers.generate.generation_service.run_social_only_pipeline", AsyncMock()),
        patch("app.workers.generate.image_service.run_image_generation", AsyncMock()) as mock_image,
    ):
        await run_generation(job_id)

    mock_image.assert_called_once_with(campaign_id, job_id, mock_db)


@pytest.mark.asyncio
async def test_run_generation_social_only_skip_image_true_skips_image_generation():
    """social_only + skip_image=True: image_service.run_image_generation not called, job complete."""
    import uuid as _uuid

    from app.workers.generate import run_generation

    job_id = _uuid.uuid4()
    campaign_id = _uuid.uuid4()

    pending_job = _make_worker_job(job_id=job_id, campaign_id=campaign_id, status="pending")
    in_progress_job = _make_worker_job(job_id=job_id, campaign_id=campaign_id, status="in_progress")
    campaign = _make_worker_campaign(skip_image=True, campaign_type="social_only")

    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=None)

    get_job_calls = {"n": 0}

    async def mock_get_job(db, jid):
        n = get_job_calls["n"]
        get_job_calls["n"] += 1
        return pending_job if n == 0 else in_progress_job

    with (
        patch("app.workers.generate.AsyncSessionLocal", return_value=mock_db),
        patch("app.workers.generate.get_job", side_effect=mock_get_job),
        patch("app.workers.generate.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.workers.generate.generation_service.run_social_only_pipeline", AsyncMock()),
        patch("app.workers.generate.image_service.run_image_generation", AsyncMock()) as mock_image,
    ):
        await run_generation(job_id)

    mock_image.assert_not_called()
    assert in_progress_job.status == "complete"
    assert in_progress_job.completed_at is not None
