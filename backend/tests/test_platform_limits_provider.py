"""Tests for provider repair-then-fallback behavior (AC: 3, 6).

Covers both gemini.py and anthropic_client.py:
- Over-limit response triggers exactly one repair call
- Repaired output used when within limit
- Sentence-boundary fallback when repair still over
- No ellipsis in output
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_gemini_response(text: str):
    mock_response = MagicMock()
    mock_response.text = text
    return mock_response


def _make_gemini_social_json(x_post="", linkedin_post="", instagram_caption="", facebook_post="", threads_post=""):
    return json.dumps({
        "x_post": x_post or "Short tweet here.",
        "linkedin_post": linkedin_post or ("LinkedIn content. " * 20),  # ~340 chars
        "instagram_caption": instagram_caption or ("A" * 200),
        "facebook_post": facebook_post or ("B" * 250),
        "threads_post": threads_post or ("C" * 100),
    })


def _make_anthropic_response(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


_VALID_BVP = {
    "tone": ["professional"],
    "cadence": {"avg_sentence_length": 15},
    "banned_jargon": [],
}

_VALID_BLOG_HTML = "<h1>Test</h1><p>Blog content here.</p>"


# ══════════════════════════════════════════════════════════════════════════════
# Gemini: generate_social repair tests
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_gemini_generate_social_x_over_limit_triggers_repair(mock_client):
    """Over-limit X post triggers exactly one repair call; repaired result used."""
    from app.integrations.gemini import generate_social

    over_limit_x = "x" * 300  # 300 > 280
    repaired_x = "x" * 270    # 270 <= 280

    original_json = _make_gemini_social_json(x_post=over_limit_x)
    repair_response = _make_gemini_response(repaired_x)

    call_count = 0

    async def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _make_gemini_response(original_json)
        else:
            return repair_response

    mock_client.aio.models.generate_content = mock_generate

    result = await generate_social(_VALID_BLOG_HTML, "Test Title", _VALID_BVP)

    assert call_count == 2, "Expected exactly one repair call"
    assert result["x_post"] == repaired_x
    assert "…" not in result["x_post"]


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_gemini_generate_social_x_over_limit_repair_fails_uses_sentence_boundary(mock_client):
    """When repair still over limit, falls back to sentence-boundary truncation."""
    from app.integrations.gemini import generate_social

    # X post is 300 chars, over 280
    over_limit_x = "First sentence. " + "x" * 285
    # Repair also over limit
    still_over_x = "y" * 285

    original_json = _make_gemini_social_json(x_post=over_limit_x)

    call_count = 0

    async def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _make_gemini_response(original_json)
        else:
            return _make_gemini_response(still_over_x)

    mock_client.aio.models.generate_content = mock_generate

    result = await generate_social(_VALID_BLOG_HTML, "Test Title", _VALID_BVP)

    assert call_count == 2, "Expected exactly one repair call then fallback"
    assert len(result["x_post"]) <= 280
    assert "…" not in result["x_post"]


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_gemini_generate_social_within_limit_no_repair_called(mock_client):
    """Posts within limits generate no repair calls."""
    from app.integrations.gemini import generate_social

    valid_json = _make_gemini_social_json()  # all well within limits

    call_count = 0

    async def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return _make_gemini_response(valid_json)

    mock_client.aio.models.generate_content = mock_generate

    result = await generate_social(_VALID_BLOG_HTML, "Test Title", _VALID_BVP)

    assert call_count == 1, "No repair should have been called"
    assert result["x_post"] is not None


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_gemini_generate_social_threads_over_limit_triggers_repair(mock_client):
    """Threads post over 500 chars triggers repair."""
    from app.integrations.gemini import generate_social

    over_limit_threads = "T" * 510  # over 500
    repaired_threads = "T" * 490   # within 500

    original_json = _make_gemini_social_json(threads_post=over_limit_threads)

    call_count = 0

    async def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _make_gemini_response(original_json)
        else:
            return _make_gemini_response(repaired_threads)

    mock_client.aio.models.generate_content = mock_generate

    result = await generate_social(_VALID_BLOG_HTML, "Test Title", _VALID_BVP)

    assert result["threads_post"] == repaired_threads
    assert "…" not in result["threads_post"]


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_gemini_generate_social_standalone_x_over_limit_triggers_repair(mock_client):
    """generate_social_standalone also repairs over-limit X posts."""
    from app.integrations.gemini import generate_social_standalone

    over_limit_x = "x" * 300
    repaired_x = "x" * 270

    original_json = _make_gemini_social_json(x_post=over_limit_x)

    call_count = 0

    async def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _make_gemini_response(original_json)
        else:
            return _make_gemini_response(repaired_x)

    mock_client.aio.models.generate_content = mock_generate

    result = await generate_social_standalone("Some brain dump content", _VALID_BVP)

    assert result["x_post"] == repaired_x
    assert "…" not in result["x_post"]


# ══════════════════════════════════════════════════════════════════════════════
# Anthropic: generate_social repair tests
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_anthropic_generate_social_x_over_limit_triggers_repair(mock_client):
    """Anthropic: over-limit X post triggers exactly one repair call."""
    from app.integrations.anthropic_client import generate_social

    over_limit_x = "x" * 300
    repaired_x = "x" * 270

    original_json = _make_gemini_social_json(x_post=over_limit_x)

    call_count = 0

    async def mock_create(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _make_anthropic_response(original_json)
        else:
            return _make_anthropic_response(repaired_x)

    mock_client.messages.create = mock_create

    result = await generate_social(_VALID_BLOG_HTML, "Test Title", _VALID_BVP)

    assert call_count == 2, "Expected exactly one repair call"
    assert result["x_post"] == repaired_x
    assert "…" not in result["x_post"]


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_anthropic_generate_social_x_over_limit_repair_fails_uses_sentence_boundary(mock_client):
    """Anthropic: when repair still over limit, falls back to sentence-boundary."""
    from app.integrations.anthropic_client import generate_social

    over_limit_x = "First sentence. " + "x" * 285
    still_over_x = "y" * 285

    original_json = _make_gemini_social_json(x_post=over_limit_x)

    call_count = 0

    async def mock_create(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _make_anthropic_response(original_json)
        else:
            return _make_anthropic_response(still_over_x)

    mock_client.messages.create = mock_create

    result = await generate_social(_VALID_BLOG_HTML, "Test Title", _VALID_BVP)

    assert call_count == 2, "Expected exactly one repair call then fallback"
    assert len(result["x_post"]) <= 280
    assert "…" not in result["x_post"]


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_anthropic_generate_social_within_limit_no_repair_called(mock_client):
    """Anthropic: posts within limits generate no repair calls."""
    from app.integrations.anthropic_client import generate_social

    valid_json = _make_gemini_social_json()

    call_count = 0

    async def mock_create(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return _make_anthropic_response(valid_json)

    mock_client.messages.create = mock_create

    result = await generate_social(_VALID_BLOG_HTML, "Test Title", _VALID_BVP)

    assert call_count == 1, "No repair should have been called"
    assert result["x_post"] is not None


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_anthropic_generate_social_standalone_x_over_limit_triggers_repair(mock_client):
    """Anthropic standalone: over-limit X post triggers repair."""
    from app.integrations.anthropic_client import generate_social_standalone

    over_limit_x = "x" * 300
    repaired_x = "x" * 270

    original_json = _make_gemini_social_json(x_post=over_limit_x)

    call_count = 0

    async def mock_create(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _make_anthropic_response(original_json)
        else:
            return _make_anthropic_response(repaired_x)

    mock_client.messages.create = mock_create

    result = await generate_social_standalone("Some brain dump content", _VALID_BVP)

    assert result["x_post"] == repaired_x
    assert "…" not in result["x_post"]


# ══════════════════════════════════════════════════════════════════════════════
# Publish-time over-limit rejection tests
# ══════════════════════════════════════════════════════════════════════════════

def _make_campaign(x_post=None, linkedin_post=None, threads_post=None,
                   instagram_caption=None, facebook_post=None, image_url=None):
    campaign = MagicMock()
    campaign.id = "test-campaign-id"
    campaign.client_id = "test-client-id"
    campaign.x_post = x_post
    campaign.linkedin_post = linkedin_post
    campaign.threads_post = threads_post
    campaign.instagram_caption = instagram_caption
    campaign.facebook_post = facebook_post
    campaign.image_url = image_url
    campaign.blog_html = None
    return campaign


def _make_connection(platform: str):
    import json as _json
    from app.core.security import encrypt_credential
    conn = MagicMock()
    conn.platform = platform
    creds = {"access_token": "fake_token", "target": "personal"}
    conn.encrypted_credentials = encrypt_credential(_json.dumps(creds))
    return conn


@pytest.mark.asyncio
async def test_dispatch_publish_for_platform_x_over_limit_rejected_before_api():
    """X over-limit: returns failed+over_limit result, Twitter API NOT called."""
    from app.services.publishing import dispatch_publish_for_platform

    over_limit_x = "x" * 300  # over 280
    campaign = _make_campaign(x_post=over_limit_x)
    db = AsyncMock()

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.services.publishing.get_connection_for_platform", AsyncMock(return_value=_make_connection("x"))),
        patch("app.services.publishing.twitter_integration") as mock_twitter,
    ):
        result = await dispatch_publish_for_platform(db, campaign.id, "x")

    assert result.get("x") == "failed" or "over_limit" in str(result)
    mock_twitter.create_tweet.assert_not_called()
    mock_twitter.create_tweet_with_media.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_publish_for_platform_linkedin_over_limit_rejected_before_api():
    """LinkedIn over-limit: returns failed+over_limit, LinkedIn API NOT called."""
    from app.services.publishing import dispatch_publish_for_platform

    over_limit_li = "a" * 3001  # over 3000
    campaign = _make_campaign(linkedin_post=over_limit_li)
    db = AsyncMock()

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.services.publishing.get_connection_for_platform", AsyncMock(return_value=_make_connection("linkedin"))),
        patch("app.services.publishing.linkedin_integration") as mock_linkedin,
    ):
        result = await dispatch_publish_for_platform(db, campaign.id, "linkedin")

    assert "over_limit" in str(result)
    mock_linkedin.create_ugc_post.assert_not_called()
    mock_linkedin.create_post_with_image.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_publish_for_platform_threads_over_limit_rejected_before_api():
    """Threads over-limit: returns failed+over_limit, API NOT called."""
    from app.services.publishing import dispatch_publish_for_platform

    over_limit_threads = "t" * 510  # over 500
    campaign = _make_campaign(threads_post=over_limit_threads)
    db = AsyncMock()

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.services.publishing.get_connection_for_platform", AsyncMock(return_value=_make_connection("threads"))),
        patch("app.services.publishing._refresh_threads_token_if_needed", AsyncMock(side_effect=lambda creds, *a, **kw: creds)),
        patch("app.services.publishing.meta_integration") as mock_meta,
    ):
        result = await dispatch_publish_for_platform(db, campaign.id, "threads")

    assert "over_limit" in str(result)
    mock_meta.publish_threads_post.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_publish_bulk_x_over_limit_skips_api_sets_over_limit_result():
    """dispatch_publish bulk path: over-limit X sets result to 'over_limit', Twitter NOT called."""
    from app.services.publishing import dispatch_publish

    over_limit_x = "x" * 300  # over 280
    campaign = _make_campaign(x_post=over_limit_x)
    db = AsyncMock()

    # Build a minimal connections list for the x platform only
    connections = [_make_connection("x")]

    import uuid as _uuid
    fake_job_id = _uuid.UUID("00000000-0000-0000-0000-000000000001")

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.services.publishing.get_connections_for_client", AsyncMock(return_value=connections)),
        patch("app.services.publishing.twitter_integration") as mock_twitter,
    ):
        result = await dispatch_publish(db, campaign.id, fake_job_id)

    assert result.get("x") == "over_limit", f"Expected 'over_limit' for x, got: {result}"
    mock_twitter.create_tweet.assert_not_called()
    mock_twitter.create_tweet_with_media.assert_not_called()
