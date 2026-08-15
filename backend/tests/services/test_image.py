"""Unit tests for services/image.py with mocked image provider and Supabase calls."""
import asyncio
import uuid
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
    campaign.x_post = None
    campaign.linkedin_post = None
    campaign.brain_dump = None
    campaign.excerpt = None
    campaign.target_keyword = None
    campaign.target_audience = None
    campaign.image_url = None
    campaign.image_alt = None
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
@patch("app.services.image._img")
async def test_happy_path_image_url_set_job_complete(
    mock_img, mock_sub_svc, mock_storage, mock_logs
):
    """Happy path: provider succeeds → image_url + image_alt set, job complete, log created."""
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
    mock_img.generate_image = AsyncMock(return_value="https://replicate.delivery/image.png")
    mock_storage.upload_image_from_url = AsyncMock(
        return_value="https://supabase.co/storage/v1/object/public/generated-images/test/test-blog-title.png"
    )
    mock_logs.create_generation_log = AsyncMock()

    await run_image_generation(campaign_id, job_id, db)

    assert campaign.image_url == "https://supabase.co/storage/v1/object/public/generated-images/test/test-blog-title.png"
    assert campaign.image_alt == "Test Blog Title – featured article image"
    assert job.status == "complete"
    assert job.completed_at is not None
    mock_logs.create_generation_log.assert_called_once()
    call_kwargs = mock_logs.create_generation_log.call_args.kwargs
    assert call_kwargs["replicate_count"] == 1


@pytest.mark.asyncio
@patch("app.services.image.supabase_storage")
@patch("app.services.image.subscription_service")
@patch("app.services.image._img")
async def test_image_limit_reached_job_complete_image_url_null(
    mock_img, mock_sub_svc, mock_storage
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
    assert job.error_details is not None
    assert "image generation skipped" in job.error_details.lower()
    mock_img.generate_image.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.image.supabase_storage")
@patch("app.services.image.subscription_service")
@patch("app.services.image._img")
async def test_run_image_generation_limit_reached_sets_error_details(
    mock_img, mock_sub_svc, mock_storage
):
    """Image limit reached: job.error_details contains 'image generation skipped' before commit."""
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

    assert job.status == "complete"
    assert job.error_details is not None
    assert "image generation skipped" in job.error_details.lower()
    assert "billing cycle" in job.error_details.lower()
    db.commit.assert_called()


@pytest.mark.asyncio
@patch("app.services.image.generation_logs_repo")
@patch("app.services.image.supabase_storage")
@patch("app.services.image.subscription_service")
@patch("app.services.image._img")
async def test_provider_fails_after_retries_job_complete_with_error_details(
    mock_img, mock_sub_svc, mock_storage, mock_logs
):
    """Provider fails after 3 retries → job complete with error_details, campaign proceeds."""
    from app.services.image import run_image_generation

    campaign_id = uuid.uuid4()
    job_id = uuid.uuid4()
    campaign = _make_campaign()
    campaign.id = campaign_id
    job = _make_job(campaign_id=campaign_id)
    client = _make_client()
    db = _make_db(job, campaign, client)

    mock_sub_svc.check_image_limit = AsyncMock()
    mock_img.generate_image = AsyncMock(side_effect=RuntimeError("Provider API error"))

    with patch("app.services.image.asyncio.sleep", new=AsyncMock()):
        await run_image_generation(campaign_id, job_id, db)

    assert campaign.image_url is None
    assert job.status == "complete"
    assert "Image generation failed" in (job.error_details or "")
    mock_storage.upload_image_from_url.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.image.supabase_storage")
@patch("app.services.image.subscription_service")
@patch("app.services.image._img")
async def test_regenerate_within_limit_returns_new_url_and_alt(
    mock_img, mock_sub_svc, mock_storage
):
    """Regenerate: within limit → new image_url + image_alt returned, regen_count incremented."""
    from app.services.image import regenerate_image

    campaign_id = uuid.uuid4()
    user_id = uuid.uuid4()
    campaign = _make_campaign(image_regen_count=1)
    campaign.id = campaign_id
    job = _make_job()
    client = _make_client()
    db = _make_db(job, campaign, client)

    mock_sub_svc.check_image_limit = AsyncMock()
    mock_img.generate_image = AsyncMock(return_value="https://replicate.delivery/new.png")
    mock_storage.upload_image_from_url = AsyncMock(return_value="https://supabase.co/new.png")

    url, image_alt, count = await regenerate_image(campaign_id, user_id, db)

    assert url == "https://supabase.co/new.png"
    assert image_alt == "Test Blog Title – featured article image"
    assert count == 2
    assert campaign.image_url == "https://supabase.co/new.png"
    assert campaign.image_alt == "Test Blog Title – featured article image"
    assert campaign.image_regen_count == 2


@pytest.mark.asyncio
@patch("app.services.image.subscription_service")
@patch("app.services.image._img")
async def test_regenerate_at_limit_raises_400(mock_img, mock_sub_svc):
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
    mock_img.generate_image.assert_not_called()


# ── _build_image_prompt tests ──────────────────────────────────────────────────

def test_build_image_prompt_no_brand_voice_natural_sentences():
    """No brand voice → output starts with 'image for the article titled', no 'photograph'."""
    from app.services.image import _build_image_prompt

    result = _build_image_prompt("5 Ways to Scale Your SaaS Business", None)

    assert result.startswith("A professional editorial image for the article titled")
    assert "5 Ways to Scale Your SaaS Business" in result
    assert "no text overlays, watermarks, or logos" in result
    assert "16:9 hero banner" not in result
    assert "photograph" not in result
    assert not result.startswith("corporate editorial style,")
    assert "photorealistic" not in result
    assert "high resolution" not in result


def test_build_image_prompt_does_not_contain_16_9_reference():
    """Prompt must not contain '16:9', 'hero banner', 'wide', or 'landscape'."""
    from app.services.image import _build_image_prompt

    result = _build_image_prompt("Any Blog Title", {"tone": ["professional"]})

    assert "16:9" not in result
    assert "hero banner" not in result
    assert "wide" not in result.lower()
    assert "landscape" not in result.lower()


def test_build_image_prompt_contains_centered_subject_instruction():
    """Prompt must instruct centered subject with safe margins and square format."""
    from app.services.image import _build_image_prompt

    result = _build_image_prompt("Any Blog Title", None)

    assert "Center the main subject in the frame" in result
    assert "safe margins on all sides" in result
    assert "Square format (1:1)" in result


def test_build_image_prompt_professional_tone_appears_as_sentence():
    """Professional tone → appears as descriptive sentence, not a comma-prefixed keyword."""
    from app.services.image import _build_image_prompt

    result = _build_image_prompt("My Blog Post", {"tone": ["professional"]})

    assert "The image has a clean, corporate editorial aesthetic." in result
    assert "corporate editorial style," not in result


def test_build_image_prompt_two_tones_joined_with_and():
    """Two tones → combined with 'and' in a single sentence."""
    from app.services.image import _build_image_prompt

    result = _build_image_prompt("My Blog Post", {"tone": ["professional", "friendly"]})

    assert "clean, corporate editorial aesthetic and inviting, human-centered composition" in result
    assert "The image has a" in result


def test_build_image_prompt_unknown_tone_used_verbatim():
    """Unknown tone key → produces a grammatically complete sentence via 'visual style' suffix."""
    from app.services.image import _build_image_prompt

    result = _build_image_prompt("My Post", {"tone": ["mysterious"]})

    assert "The image has a mysterious visual style." in result


def test_build_image_prompt_empty_tone_list_no_tone_sentence():
    """Empty tone list → no tone sentence in output."""
    from app.services.image import _build_image_prompt

    result = _build_image_prompt("My Post", {"tone": []})

    assert "The image has a" not in result


def test_build_image_prompt_only_first_two_tones_used():
    """More than two tones → only first two are incorporated."""
    from app.services.image import _build_image_prompt

    result = _build_image_prompt("My Post", {"tone": ["professional", "casual", "formal"]})

    assert "clean, corporate editorial aesthetic" in result
    assert "warm, approachable lifestyle atmosphere" in result
    assert "minimalist, refined editorial look" not in result


def test_build_image_prompt_no_photograph_word():
    """'photograph' must not appear anywhere in the generated prompt."""
    from app.services.image import _build_image_prompt

    result = _build_image_prompt("Any Title", {"tone": ["professional"]})

    assert "photograph" not in result


# ── _build_image_alt tests ─────────────────────────────────────────────────────

def test_build_image_alt_standard_title():
    """Standard title → format '{title} – featured article image'."""
    from app.services.image import _build_image_alt

    result = _build_image_alt("5 Ways to Scale Your SaaS Business")

    assert result == "5 Ways to Scale Your SaaS Business – featured article image"


def test_build_image_alt_truncates_at_125_chars():
    """200-char title → alt text truncated to 125 chars."""
    from app.services.image import _build_image_alt

    long_title = "A" * 200
    result = _build_image_alt(long_title)

    assert len(result) <= 125


# ── _slugify tests ─────────────────────────────────────────────────────────────

def test_slugify_standard_title():
    """Standard title with punctuation → lowercase hyphen slug."""
    from app.services.image import _slugify

    result = _slugify("5 Ways to Scale Your SaaS Business!")

    assert result == "5-ways-to-scale-your-saas-business"


def test_slugify_empty_string_returns_featured():
    """Empty string → 'featured' fallback."""
    from app.services.image import _slugify

    result = _slugify("")

    assert result == "featured"


def test_slugify_converts_underscores_to_hyphens():
    """Underscores are converted to hyphens for SEO-preferred filenames."""
    from app.services.image import _slugify

    result = _slugify("hello_world_post")

    assert result == "hello-world-post"


def test_slugify_truncates_at_60_chars():
    """80-char title → slug truncated to 60 chars."""
    from app.services.image import _slugify

    long_title = "word " * 16  # 80 chars
    result = _slugify(long_title)

    assert len(result) <= 60


# ── Storage path tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.services.image.generation_logs_repo")
@patch("app.services.image.supabase_storage")
@patch("app.services.image.subscription_service")
@patch("app.services.image._img")
async def test_initial_generation_storage_path_uses_title_slug(
    mock_img, mock_sub_svc, mock_storage, mock_logs
):
    """Initial generation → storage path is {campaign_id}/{title_slug}.png."""
    from app.services.image import run_image_generation

    campaign_id = uuid.uuid4()
    job_id = uuid.uuid4()
    campaign = _make_campaign()
    campaign.id = campaign_id
    campaign.blog_html = "<h1>5 Ways to Scale Your SaaS Business</h1>"
    job = _make_job(campaign_id=campaign_id)
    job.id = job_id
    client = _make_client()
    db = _make_db(job, campaign, client)

    mock_sub_svc.check_image_limit = AsyncMock()
    mock_img.generate_image = AsyncMock(return_value="https://replicate.delivery/image.png")
    mock_storage.upload_image_from_url = AsyncMock(return_value="https://supabase.co/image.png")
    mock_logs.create_generation_log = AsyncMock()

    await run_image_generation(campaign_id, job_id, db)

    expected_path = f"generated-images/{campaign_id}/5-ways-to-scale-your-saas-business.png"
    mock_storage.upload_image_from_url.assert_called_once_with(
        "https://replicate.delivery/image.png", expected_path
    )


@pytest.mark.asyncio
@patch("app.services.image.supabase_storage")
@patch("app.services.image.subscription_service")
@patch("app.services.image._img")
async def test_regen_storage_path_uses_title_slug_with_count(
    mock_img, mock_sub_svc, mock_storage
):
    """Regen N=2 → storage path is {campaign_id}/{title_slug}-2.png."""
    from app.services.image import regenerate_image

    campaign_id = uuid.uuid4()
    user_id = uuid.uuid4()
    campaign = _make_campaign(image_regen_count=1)
    campaign.id = campaign_id
    campaign.blog_html = "<h1>5 Ways to Scale Your SaaS Business</h1>"
    job = _make_job()
    client = _make_client()
    db = _make_db(job, campaign, client)

    mock_sub_svc.check_image_limit = AsyncMock()
    mock_img.generate_image = AsyncMock(return_value="https://replicate.delivery/new.png")
    mock_storage.upload_image_from_url = AsyncMock(return_value="https://supabase.co/new.png")

    await regenerate_image(campaign_id, user_id, db)

    expected_path = f"generated-images/{campaign_id}/5-ways-to-scale-your-saas-business-2.png"
    mock_storage.upload_image_from_url.assert_called_once_with(
        "https://replicate.delivery/new.png", expected_path
    )
    assert campaign.image_alt == "5 Ways to Scale Your SaaS Business – featured article image"


# ── social_only (blog_html=None) tests ────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.services.image.generation_logs_repo")
@patch("app.services.image.supabase_storage")
@patch("app.services.image.subscription_service")
@patch("app.services.image._img")
async def test_social_only_campaign_uses_linkedin_as_image_subject(
    mock_img, mock_sub_svc, mock_storage, mock_logs
):
    """social_only campaign (blog_html=None) with linkedin_post → prompt uses linkedin_post, not x_post."""
    from app.services.image import run_image_generation

    campaign_id = uuid.uuid4()
    job_id = uuid.uuid4()
    campaign = _make_campaign()
    campaign.id = campaign_id
    campaign.blog_html = None
    campaign.linkedin_post = "5 strategies for scaling a SaaS business sustainably"
    campaign.x_post = "X post hook text that should not appear"
    job = _make_job(campaign_id=campaign_id)
    job.id = job_id
    client = _make_client()
    db = _make_db(job, campaign, client)

    mock_sub_svc.check_image_limit = AsyncMock()
    mock_img.generate_image = AsyncMock(return_value="https://replicate.delivery/image.png")
    mock_storage.upload_image_from_url = AsyncMock(return_value="https://supabase.co/image.png")
    mock_logs.create_generation_log = AsyncMock()

    await run_image_generation(campaign_id, job_id, db)

    assert job.status == "complete"
    prompt_used = mock_img.generate_image.call_args[0][0]
    assert "Untitled" not in prompt_used
    assert "5 strategies for scaling a SaaS business sustainably" in prompt_used
    assert "X post hook text" not in prompt_used


@pytest.mark.asyncio
@patch("app.services.image.generation_logs_repo")
@patch("app.services.image.supabase_storage")
@patch("app.services.image.subscription_service")
@patch("app.services.image._img")
async def test_social_only_no_posts_falls_back_to_untitled(
    mock_img, mock_sub_svc, mock_storage, mock_logs
):
    """social_only campaign with no x_post or linkedin_post → falls back to 'Untitled'."""
    from app.services.image import run_image_generation

    campaign_id = uuid.uuid4()
    job_id = uuid.uuid4()
    campaign = _make_campaign()
    campaign.id = campaign_id
    campaign.blog_html = None
    campaign.x_post = None
    campaign.linkedin_post = None
    campaign.brain_dump = None
    job = _make_job(campaign_id=campaign_id)
    job.id = job_id
    client = _make_client()
    db = _make_db(job, campaign, client)

    mock_sub_svc.check_image_limit = AsyncMock()
    mock_img.generate_image = AsyncMock(return_value="https://replicate.delivery/image.png")
    mock_storage.upload_image_from_url = AsyncMock(return_value="https://supabase.co/image.png")
    mock_logs.create_generation_log = AsyncMock()

    await run_image_generation(campaign_id, job_id, db)

    assert job.status == "complete"
    prompt_used = mock_img.generate_image.call_args[0][0]
    assert "Untitled" in prompt_used


# ── _generate_with_retry timeout test ─────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.services.image._img")
async def test_generate_with_retry_timeout_is_treated_as_failure(mock_img):
    """TimeoutError from wait_for is caught as a failure and retried."""
    from app.services.image import _generate_with_retry

    mock_img.generate_image = AsyncMock(side_effect=asyncio.TimeoutError())

    with patch("app.services.image.asyncio.sleep", new=AsyncMock()):
        with pytest.raises(asyncio.TimeoutError):
            await _generate_with_retry("test prompt", max_retries=2)

    assert mock_img.generate_image.call_count == 2


# ── _generate_with_retry jitter tests ─────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.services.image.random.uniform")
@patch("app.services.image._img")
async def test_generate_with_retry_first_retry_sleeps_with_jitter(mock_img, mock_uniform):
    """First retry sleep = 8 * 2^0 * jitter where jitter = random.uniform(0.8, 1.2)."""
    from app.services.image import _generate_with_retry

    mock_img.generate_image = AsyncMock(
        side_effect=[RuntimeError("timeout"), "https://replicate.delivery/image.png"]
    )
    mock_uniform.return_value = 1.1

    sleep_calls = []
    async def fake_sleep(duration):
        sleep_calls.append(duration)

    with patch("app.services.image.asyncio.sleep", side_effect=fake_sleep):
        result = await _generate_with_retry("prompt", max_retries=3)

    assert result == "https://replicate.delivery/image.png"
    assert len(sleep_calls) == 1
    mock_uniform.assert_called_once_with(0.8, 1.2)
    expected = 8 * (2 ** 0) * 1.1
    assert abs(sleep_calls[0] - expected) < 0.001


@pytest.mark.asyncio
@patch("app.services.image.random.uniform")
@patch("app.services.image._img")
async def test_generate_with_retry_second_retry_uses_doubled_base(mock_img, mock_uniform):
    """Second retry sleep = 8 * 2^1 * jitter (16s base)."""
    from app.services.image import _generate_with_retry

    mock_img.generate_image = AsyncMock(
        side_effect=[
            RuntimeError("first fail"),
            RuntimeError("second fail"),
            "https://replicate.delivery/image.png",
        ]
    )
    mock_uniform.return_value = 0.9

    sleep_calls = []
    async def fake_sleep(duration):
        sleep_calls.append(duration)

    with patch("app.services.image.asyncio.sleep", side_effect=fake_sleep):
        result = await _generate_with_retry("prompt", max_retries=3)

    assert result == "https://replicate.delivery/image.png"
    assert len(sleep_calls) == 2
    expected_second = 8 * (2 ** 1) * 0.9
    assert abs(sleep_calls[1] - expected_second) < 0.001


# ── _build_image_prompt enrichment tests (AC 2-4) ────────────────────────────

def test_build_image_prompt_with_keyword_injects_subject_sentence():
    """target_keyword provided → 'The subject of the article is ...' present in prompt."""
    from app.services.image import _build_image_prompt

    result = _build_image_prompt("How to Scale SaaS", None, target_keyword="SaaS scaling")

    assert "The subject of the article is SaaS scaling." in result


def test_build_image_prompt_with_audience_injects_audience_sentence():
    """target_audience provided → 'The intended audience is ...' present in prompt."""
    from app.services.image import _build_image_prompt

    result = _build_image_prompt("My Post", None, target_audience="startup founders")

    assert "The intended audience is startup founders." in result


def test_build_image_prompt_with_long_excerpt_capped_at_200_chars():
    """content_excerpt > 200 chars → only first 200 chars injected into prompt."""
    from app.services.image import _build_image_prompt

    long_excerpt = "X" * 300
    result = _build_image_prompt("My Post", None, content_excerpt=long_excerpt)

    assert "The article covers: " + "X" * 200 + "." in result
    assert "X" * 201 not in result


def test_build_image_prompt_no_enrichment_fields_output_unchanged():
    """No enrichment args → output identical to pre-story behavior (no extra sentences)."""
    from app.services.image import _build_image_prompt

    result = _build_image_prompt("My Blog Post", None)

    assert "The subject of the article is" not in result
    assert "The intended audience is" not in result
    assert "The article covers:" not in result
    assert result.startswith("A professional editorial image for the article titled 'My Blog Post'.")


# ── Social fallback tests for run_image_generation (AC 6) ────────────────────

@pytest.mark.asyncio
@patch("app.services.image.generation_logs_repo")
@patch("app.services.image.supabase_storage")
@patch("app.services.image.subscription_service")
@patch("app.services.image._img")
async def test_social_fallback_linkedin_preferred_over_brain_dump(
    mock_img, mock_sub_svc, mock_storage, mock_logs
):
    """blog_html=None, linkedin_post and brain_dump both set → linkedin_post wins."""
    from app.services.image import run_image_generation

    campaign_id = uuid.uuid4()
    job_id = uuid.uuid4()
    campaign = _make_campaign()
    campaign.id = campaign_id
    campaign.blog_html = None
    campaign.linkedin_post = "LinkedIn post about sustainable growth"
    campaign.brain_dump = "Raw brain dump content that should not be used"
    job = _make_job(campaign_id=campaign_id)
    job.id = job_id
    client = _make_client()
    db = _make_db(job, campaign, client)

    mock_sub_svc.check_image_limit = AsyncMock()
    mock_img.generate_image = AsyncMock(return_value="https://replicate.delivery/image.png")
    mock_storage.upload_image_from_url = AsyncMock(return_value="https://supabase.co/image.png")
    mock_logs.create_generation_log = AsyncMock()

    await run_image_generation(campaign_id, job_id, db)

    prompt_used = mock_img.generate_image.call_args[0][0]
    assert "LinkedIn post about sustainable growth" in prompt_used
    assert "Raw brain dump content" not in prompt_used


@pytest.mark.asyncio
@patch("app.services.image.generation_logs_repo")
@patch("app.services.image.supabase_storage")
@patch("app.services.image.subscription_service")
@patch("app.services.image._img")
async def test_social_fallback_brain_dump_used_when_no_linkedin(
    mock_img, mock_sub_svc, mock_storage, mock_logs
):
    """blog_html=None, linkedin_post=None, brain_dump set → brain_dump used as subject."""
    from app.services.image import run_image_generation

    campaign_id = uuid.uuid4()
    job_id = uuid.uuid4()
    campaign = _make_campaign()
    campaign.id = campaign_id
    campaign.blog_html = None
    campaign.linkedin_post = None
    campaign.brain_dump = "Brain dump: tips for remote team productivity"
    job = _make_job(campaign_id=campaign_id)
    job.id = job_id
    client = _make_client()
    db = _make_db(job, campaign, client)

    mock_sub_svc.check_image_limit = AsyncMock()
    mock_img.generate_image = AsyncMock(return_value="https://replicate.delivery/image.png")
    mock_storage.upload_image_from_url = AsyncMock(return_value="https://supabase.co/image.png")
    mock_logs.create_generation_log = AsyncMock()

    await run_image_generation(campaign_id, job_id, db)

    prompt_used = mock_img.generate_image.call_args[0][0]
    assert "Brain dump: tips for remote team productivity" in prompt_used
    assert "Untitled" not in prompt_used


# ── regenerate_image social fallback test (AC 7) ─────────────────────────────

@pytest.mark.asyncio
@patch("app.services.image.generation_logs_repo")
@patch("app.services.image.supabase_storage")
@patch("app.services.image.subscription_service")
@patch("app.services.image._img")
async def test_regenerate_image_social_fallback_uses_linkedin_not_untitled(
    mock_img, mock_sub_svc, mock_storage, mock_logs
):
    """regenerate_image with blog_html=None → uses linkedin_post as image subject, not 'Untitled'."""
    from app.services.image import regenerate_image

    campaign_id = uuid.uuid4()
    user_id = uuid.uuid4()
    campaign = _make_campaign(image_regen_count=1)
    campaign.id = campaign_id
    campaign.blog_html = None
    campaign.linkedin_post = "LinkedIn post for social-only campaign regen"
    campaign.brain_dump = None
    job = _make_job()
    client = _make_client()
    db = _make_db(job, campaign, client)

    mock_sub_svc.check_image_limit = AsyncMock()
    mock_img.generate_image = AsyncMock(return_value="https://replicate.delivery/regen.png")
    mock_storage.upload_image_from_url = AsyncMock(return_value="https://supabase.co/regen.png")
    mock_logs.create_generation_log = AsyncMock()

    url, image_alt, count = await regenerate_image(campaign_id, user_id, db)

    assert url == "https://supabase.co/regen.png"
    assert count == 2
    prompt_used = mock_img.generate_image.call_args[0][0]
    assert "LinkedIn post for social-only campaign regen" in prompt_used
    assert "Untitled" not in prompt_used


# ── _build_image_prompt combined enrichment ordering test ────────────────────

def test_build_image_prompt_combined_enrichment_sentence_order():
    """All three enrichment fields set → keyword, audience, excerpt appear in order after title, before composition."""
    from app.services.image import _build_image_prompt

    result = _build_image_prompt(
        "Scaling SaaS",
        None,
        target_keyword="SaaS scaling",
        target_audience="startup founders",
        content_excerpt="Sustainable growth strategies for B2B companies.",
    )

    title_pos = result.find("Scaling SaaS'.")
    keyword_pos = result.find("The subject of the article is SaaS scaling.")
    audience_pos = result.find("The intended audience is startup founders.")
    excerpt_pos = result.find("The article covers: Sustainable growth strategies")
    composition_pos = result.find("The composition is clean")

    assert title_pos < keyword_pos < audience_pos < excerpt_pos < composition_pos


def test_build_image_prompt_whitespace_only_keyword_suppressed():
    """Whitespace-only target_keyword → no blank subject sentence injected."""
    from app.services.image import _build_image_prompt

    result = _build_image_prompt("My Post", None, target_keyword="   ")

    assert "The subject of the article is" not in result


def test_build_image_prompt_whitespace_only_audience_suppressed():
    """Whitespace-only target_audience → no blank audience sentence injected."""
    from app.services.image import _build_image_prompt

    result = _build_image_prompt("My Post", None, target_audience="\t  ")

    assert "The intended audience is" not in result


# ── regenerate_image brain_dump fallback test (AC 7) ─────────────────────────

@pytest.mark.asyncio
@patch("app.services.image.generation_logs_repo")
@patch("app.services.image.supabase_storage")
@patch("app.services.image.subscription_service")
@patch("app.services.image._img")
async def test_regenerate_image_social_fallback_uses_brain_dump_when_no_linkedin(
    mock_img, mock_sub_svc, mock_storage, mock_logs
):
    """regenerate_image with blog_html=None, linkedin_post=None → uses brain_dump as image subject."""
    from app.services.image import regenerate_image

    campaign_id = uuid.uuid4()
    user_id = uuid.uuid4()
    campaign = _make_campaign(image_regen_count=1)
    campaign.id = campaign_id
    campaign.blog_html = None
    campaign.linkedin_post = None
    campaign.brain_dump = "Brain dump content about productivity for remote teams"
    job = _make_job()
    client = _make_client()
    db = _make_db(job, campaign, client)

    mock_sub_svc.check_image_limit = AsyncMock()
    mock_img.generate_image = AsyncMock(return_value="https://replicate.delivery/regen2.png")
    mock_storage.upload_image_from_url = AsyncMock(return_value="https://supabase.co/regen2.png")
    mock_logs.create_generation_log = AsyncMock()

    url, image_alt, count = await regenerate_image(campaign_id, user_id, db)

    assert url == "https://supabase.co/regen2.png"
    assert count == 2
    prompt_used = mock_img.generate_image.call_args[0][0]
    assert "Brain dump content about productivity" in prompt_used
    assert "Untitled" not in prompt_used
