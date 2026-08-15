"""Unit tests for integrations/anthropic_client.py (AC 9)."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_anthropic_response(text: str):
    """Build a mock Anthropic response with a single TextBlock."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


def _make_anthropic_response_with_thinking(text: str):
    """Build a mock Anthropic response with a leading ThinkingBlock then a TextBlock."""
    thinking_block = MagicMock()
    thinking_block.type = "thinking"
    thinking_block.thinking = "internal reasoning here"

    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text

    response = MagicMock()
    response.content = [thinking_block, text_block]
    return response


_VALID_BVP = {
    "tone": ["authoritative", "direct"],
    "cadence": {"avg_sentence_length": 18, "variation_pattern": "short", "paragraph_structure": "3-5 sentences"},
    "banned_jargon": ["leverage", "synergy"],
}

_VALID_BLOG_HTML = (
    '<h1>Test Title</h1>'
    '<div class="tldr"><p><strong>TL;DR:</strong> Summary here.</p></div>'
    "<h2>Section One</h2><h3>Sub</h3><p>Body paragraph.</p>"
    "<h2>Section Two</h2><h3>Sub</h3><p>More body.</p>"
    "<h2>Section Three</h2><h3>Sub</h3><p>Even more.</p>"
    '<h2>Frequently Asked Questions</h2>'
    '<dl class="faq"><dt>Q1</dt><dd>A1</dd><dt>Q2</dt><dd>A2</dd><dt>Q3</dt><dd>A3</dd></dl>'
    "<h2>What to Do Next</h2><p>Conclusion text.</p>"
)

_VALID_FIDELITY_JSON = json.dumps({
    "tone_score": 8,
    "cadence_score": 7,
    "jargon_violations": 0,
    "seo_bluf_present": True,
    "seo_h2_count": 4,
    "seo_faq_present": True,
    "seo_fluff_detected": False,
    "tags": ["content marketing", "ai writing", "brand voice"],
})

_VALID_SOCIAL_JSON = json.dumps({
    "x_post": "Check out this blog post about testing!",
    "linkedin_post": "We published a new article. " * 25,  # ~625 chars
    "instagram_caption": "A" * 200,
    "facebook_post": "B" * 250,
    "threads_post": "C" * 100,
})


# ── generate_blog (no thinking) ───────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_blog_returns_html(mock_client):
    from app.integrations.anthropic_client import generate_blog

    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response(_VALID_BLOG_HTML)
    )
    result = await generate_blog("My brain dump idea", _VALID_BVP, thinking_tokens=0)
    assert "<h1>" in result


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_blog_emdash_replaced(mock_client):
    from app.integrations.anthropic_client import generate_blog

    html_with_emdash = _VALID_BLOG_HTML.replace("Summary here.", "Summary—here.")
    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response(html_with_emdash)
    )
    result = await generate_blog("dump", _VALID_BVP, thinking_tokens=0)
    assert "—" not in result


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_blog_injects_tldr_when_missing(mock_client):
    from app.integrations.anthropic_client import generate_blog

    html_no_tldr = "<h1>Test Title</h1><h2>S1</h2><p>body</p><h2>S2</h2><p>body2</p>"
    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response(html_no_tldr)
    )
    result = await generate_blog("dump", _VALID_BVP, thinking_tokens=0)

    assert '<div class="tldr">' in result
    assert "TL;DR:" in result
    assert "[Summary pending review]" in result
    h1_close = result.find("</h1>")
    tldr_pos = result.find('<div class="tldr">')
    assert tldr_pos == h1_close + len("</h1>")


# ── generate_blog (with thinking) ─────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_blog_with_thinking_passes_thinking_param(mock_client):
    """When thinking_tokens=512, messages.create is called with thinking param and beta header."""
    from app.integrations.anthropic_client import generate_blog

    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response(_VALID_BLOG_HTML)
    )
    await generate_blog("dump", _VALID_BVP, thinking_tokens=512)

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs.get("thinking") == {"type": "enabled", "budget_tokens": 512}
    assert call_kwargs.get("extra_headers") == {"anthropic-beta": "interleaved-thinking-2025-05-14"}


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_blog_with_thinking_extracts_text_from_second_block(mock_client):
    """When thinking blocks precede the text block, next(b.text) still returns the text."""
    from app.integrations.anthropic_client import generate_blog

    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response_with_thinking(_VALID_BLOG_HTML)
    )
    result = await generate_blog("dump", _VALID_BVP, thinking_tokens=512)
    assert "<h1>" in result


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_blog_no_thinking_when_tokens_zero(mock_client):
    """When thinking_tokens=0, no thinking param is sent."""
    from app.integrations.anthropic_client import generate_blog

    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response(_VALID_BLOG_HTML)
    )
    await generate_blog("dump", _VALID_BVP, thinking_tokens=0)

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert "thinking" not in call_kwargs
    assert "extra_headers" not in call_kwargs


# ── check_fidelity ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_check_fidelity_happy_path(mock_client):
    from app.integrations.anthropic_client import check_fidelity

    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response(_VALID_FIDELITY_JSON)
    )
    result = await check_fidelity(_VALID_BLOG_HTML, _VALID_BVP)
    assert result["tone_score"] == 8
    assert result["cadence_score"] == 7
    assert result["jargon_violations"] == 0
    assert result["seo_bluf_present"] is True
    assert result["seo_h2_count"] == 4
    assert result["seo_faq_present"] is True
    assert result["seo_fluff_detected"] is False


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_check_fidelity_none_bvp_returns_default_without_api_call(mock_client):
    from app.integrations.anthropic_client import check_fidelity

    result = await check_fidelity(_VALID_BLOG_HTML, None)
    mock_client.messages.create.assert_not_called()
    assert result == {
        "tone_score": 10,
        "cadence_score": 10,
        "jargon_violations": 0,
        "seo_bluf_present": True,
        "seo_h2_count": 3,
        "seo_faq_present": True,
        "seo_fluff_detected": False,
        "authored_passages_preserved": True,
        "tags": [],
    }


# ── generate_social ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_social_happy_path(mock_client):
    from app.integrations.anthropic_client import generate_social

    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response(_VALID_SOCIAL_JSON)
    )
    result = await generate_social("brain dump", "Test Title", _VALID_BVP)
    assert "x_post" in result
    assert "linkedin_post" in result


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_social_truncates_x_post_at_280(mock_client):
    from app.integrations.anthropic_client import generate_social

    long_x = "x" * 300
    data = json.dumps({
        "x_post": long_x, "linkedin_post": "LinkedIn post " * 40,
        "instagram_caption": "A" * 200, "facebook_post": "B" * 250, "threads_post": "C" * 100,
    })
    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response(data)
    )
    result = await generate_social("brain dump", "Title", _VALID_BVP)
    assert len(result["x_post"]) == 280
    assert result["x_post"].endswith("…")


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_social_logs_warning_for_short_linkedin(mock_client, caplog):
    import logging
    from app.integrations.anthropic_client import generate_social

    short_ln = json.dumps({
        "x_post": "Short X post here.", "linkedin_post": "Too short.",
        "instagram_caption": "A" * 200, "facebook_post": "B" * 250, "threads_post": "C" * 100,
    })
    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response(short_ln)
    )
    with caplog.at_level(logging.WARNING, logger="app.integrations.anthropic_client"):
        await generate_social("brain dump", "Title", _VALID_BVP)
    assert any("500" in r.message or "below" in r.message for r in caplog.records)


# ── generate_social_standalone ────────────────────────────────────────────────

_VALID_STANDALONE_SOCIAL_JSON = json.dumps({
    "x_post": "I tested 4 Facebook ad setups. One crushed it. Here is what I found.",
    "linkedin_post": "LinkedIn standalone post. " * 55,  # ~1375 chars
    "instagram_caption": "A" * 200,
    "facebook_post": "B" * 250,
    "threads_post": "C" * 100,
})

_BVP_WITH_STRUCTURE_HINTS = {
    **_VALID_BVP,
    "opening_pattern": "bold_claim",
    "closing_pattern": "cta",
    "post_structure_template": "hook -- pain -- insight -- example -- CTA",
}


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_social_standalone_happy_path(mock_client):
    from app.integrations.anthropic_client import generate_social_standalone

    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response(_VALID_STANDALONE_SOCIAL_JSON)
    )
    result = await generate_social_standalone("brain dump", _VALID_BVP)
    assert "x_post" in result
    assert "linkedin_post" in result
    assert isinstance(result["x_post"], str)
    assert isinstance(result["linkedin_post"], str)


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_social_standalone_linkedin_over_2500_truncated(mock_client):
    from app.integrations.anthropic_client import generate_social_standalone

    long_ln = "L" * 2600
    data = json.dumps({
        "x_post": "Short X post.", "linkedin_post": long_ln,
        "instagram_caption": "A" * 200, "facebook_post": "B" * 250, "threads_post": "C" * 100,
    })
    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response(data)
    )
    result = await generate_social_standalone("brain dump", _VALID_BVP)
    assert len(result["linkedin_post"]) == 2500
    assert result["linkedin_post"].endswith("…")


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_social_standalone_linkedin_under_1200_logs_warning(mock_client, caplog):
    import logging
    from app.integrations.anthropic_client import generate_social_standalone

    short_data = json.dumps({
        "x_post": "Short X post.", "linkedin_post": "Too short for LinkedIn.",
        "instagram_caption": "A" * 200, "facebook_post": "B" * 250, "threads_post": "C" * 100,
    })
    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response(short_data)
    )
    with caplog.at_level(logging.WARNING, logger="app.integrations.anthropic_client"):
        await generate_social_standalone("brain dump", _VALID_BVP)
    assert any("1200" in r.message or "below" in r.message for r in caplog.records)


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_social_standalone_x_post_no_read_the_full_guide(mock_client):
    from app.integrations.anthropic_client import generate_social_standalone

    captured_prompts = []

    async def capture_call(*args, **kwargs):
        captured_prompts.append(kwargs.get("messages", [{}])[0].get("content", ""))
        return _make_anthropic_response(_VALID_STANDALONE_SOCIAL_JSON)

    mock_client.messages.create = AsyncMock(side_effect=capture_call)
    await generate_social_standalone("brain dump", _VALID_BVP)

    prompt_text = captured_prompts[0]
    assert "no 'Read the full guide'" in prompt_text


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_social_standalone_emdash_stripped_from_both_posts(mock_client):
    from app.integrations.anthropic_client import generate_social_standalone

    data_with_emdash = json.dumps({
        "x_post": "Great insight—here is what works.",
        "linkedin_post": ("LinkedIn post with em-dash—example. " * 40),
        "instagram_caption": "A" * 200,
        "facebook_post": "B" * 250,
        "threads_post": "C" * 100,
    })
    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response(data_with_emdash)
    )
    result = await generate_social_standalone("brain dump", _VALID_BVP)
    assert "—" not in result["x_post"]
    assert "—" not in result["linkedin_post"]


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_social_standalone_bvp_structure_hints_injected_into_prompt(mock_client):
    from app.integrations.anthropic_client import generate_social_standalone

    captured_prompts = []

    async def capture_call(*args, **kwargs):
        captured_prompts.append(kwargs.get("messages", [{}])[0].get("content", ""))
        return _make_anthropic_response(_VALID_STANDALONE_SOCIAL_JSON)

    mock_client.messages.create = AsyncMock(side_effect=capture_call)
    await generate_social_standalone("brain dump", _BVP_WITH_STRUCTURE_HINTS)

    prompt_text = captured_prompts[0]
    assert "BRAND STRUCTURE HINTS" in prompt_text
    assert "hook -- pain -- insight -- example -- CTA" in prompt_text


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_social_standalone_uses_standalone_prompt(mock_client):
    from app.integrations.anthropic_client import generate_social_standalone

    captured_prompts = []

    async def capture_call(*args, **kwargs):
        captured_prompts.append(kwargs.get("messages", [{}])[0].get("content", ""))
        return _make_anthropic_response(_VALID_STANDALONE_SOCIAL_JSON)

    mock_client.messages.create = AsyncMock(side_effect=capture_call)
    await generate_social_standalone("brain dump", _VALID_BVP)

    prompt_text = captured_prompts[0]
    assert "stand alone" in prompt_text
    assert "no blog article" in prompt_text
    assert "tease the blog" not in prompt_text


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_social_standalone_none_bvp_uses_default_voice(mock_client):
    from app.integrations.anthropic_client import generate_social_standalone

    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response(_VALID_STANDALONE_SOCIAL_JSON)
    )
    result = await generate_social_standalone("brain dump", None)
    assert "x_post" in result
    assert "linkedin_post" in result


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_social_emdash_stripped_from_both_posts(mock_client):
    from app.integrations.anthropic_client import generate_social

    data_with_emdash = json.dumps({
        "x_post": "Great insight—here is what works.",
        "linkedin_post": ("LinkedIn post with em-dash—example. " * 20),
        "instagram_caption": "A" * 200,
        "facebook_post": "B" * 250,
        "threads_post": "C" * 100,
    })
    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response(data_with_emdash)
    )
    result = await generate_social("brain dump", "Blog Title", _VALID_BVP)
    assert "—" not in result["x_post"]
    assert "—" not in result["linkedin_post"]


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_social_standalone_no_brand_structure_hints_when_bvp_fields_absent(mock_client):
    from app.integrations.anthropic_client import generate_social_standalone

    captured_prompts = []

    async def capture_call(*args, **kwargs):
        captured_prompts.append(kwargs.get("messages", [{}])[0].get("content", ""))
        return _make_anthropic_response(_VALID_STANDALONE_SOCIAL_JSON)

    mock_client.messages.create = AsyncMock(side_effect=capture_call)
    await generate_social_standalone("brain dump", _VALID_BVP)

    prompt_text = captured_prompts[0]
    assert "BRAND STRUCTURE HINTS" not in prompt_text


# ── Story 3.26: Social voice parity and prompt quality ───────────────────────

_BVP_WITH_VOICE_BRIEF_SOCIAL = {
    "tone": ["casual", "direct"],
    "cadence": {"avg_sentence_length": 14},
    "banned_jargon": ["leverage"],
    "voice_brief": "Boris writes raw and direct. He never hedges.",
}


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_social_uses_max_tokens_4096(mock_client):
    from app.integrations.anthropic_client import generate_social

    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response(_VALID_SOCIAL_JSON)
    )
    await generate_social("brain dump", "Title", _VALID_BVP)

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["max_tokens"] == 4096


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_social_standalone_uses_max_tokens_6144(mock_client):
    from app.integrations.anthropic_client import generate_social_standalone

    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response(_VALID_STANDALONE_SOCIAL_JSON)
    )
    await generate_social_standalone("brain dump", _VALID_BVP)

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["max_tokens"] == 6144


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_social_injects_threads_voice_section_when_voice_brief_present(mock_client):
    from app.integrations.anthropic_client import generate_social

    captured_prompts = []

    async def capture_call(*args, **kwargs):
        captured_prompts.append(kwargs.get("messages", [{}])[0].get("content", ""))
        return _make_anthropic_response(_VALID_SOCIAL_JSON)

    mock_client.messages.create = AsyncMock(side_effect=capture_call)
    await generate_social("brain dump", "Title", _BVP_WITH_VOICE_BRIEF_SOCIAL)

    prompt_text = captured_prompts[0]
    assert "THREADS BRAND VOICE" in prompt_text
    assert "Boris writes raw and direct" in prompt_text


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_social_hard_truncates_instagram_at_600(mock_client):
    from app.integrations.anthropic_client import generate_social

    long_ig = "I" * 601
    data = json.dumps({
        "x_post": "Short post.", "linkedin_post": "L" * 400,
        "instagram_caption": long_ig, "facebook_post": "F" * 300, "threads_post": "T" * 100,
    })
    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response(data)
    )
    result = await generate_social("brain dump", "Title", _VALID_BVP)
    assert len(result["instagram_caption"]) == 600
    assert result["instagram_caption"].endswith("…")


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_social_hard_truncates_facebook_at_800(mock_client):
    from app.integrations.anthropic_client import generate_social

    long_fb = "F" * 801
    data = json.dumps({
        "x_post": "Short post.", "linkedin_post": "L" * 400,
        "instagram_caption": "I" * 200, "facebook_post": long_fb, "threads_post": "T" * 100,
    })
    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response(data)
    )
    result = await generate_social("brain dump", "Title", _VALID_BVP)
    assert len(result["facebook_post"]) == 800
    assert result["facebook_post"].endswith("…")


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_social_standalone_hard_truncates_instagram_at_600(mock_client):
    from app.integrations.anthropic_client import generate_social_standalone

    long_ig = "I" * 601
    data = json.dumps({
        "x_post": "Short post but at least 70 characters to be valid for standalone.",
        "linkedin_post": "L" * 1300,
        "instagram_caption": long_ig, "facebook_post": "F" * 300, "threads_post": "T" * 100,
    })
    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response(data)
    )
    result = await generate_social_standalone("brain dump", _VALID_BVP)
    assert len(result["instagram_caption"]) == 600
    assert result["instagram_caption"].endswith("…")


@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_social_standalone_hard_truncates_facebook_at_800(mock_client):
    from app.integrations.anthropic_client import generate_social_standalone

    long_fb = "F" * 801
    data = json.dumps({
        "x_post": "Short post but at least 70 characters to be valid for standalone.",
        "linkedin_post": "L" * 1300,
        "instagram_caption": "I" * 200, "facebook_post": long_fb, "threads_post": "T" * 100,
    })
    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response(data)
    )
    result = await generate_social_standalone("brain dump", _VALID_BVP)
    assert len(result["facebook_post"]) == 800
    assert result["facebook_post"].endswith("…")
