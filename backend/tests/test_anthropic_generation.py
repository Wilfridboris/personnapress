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
    data = json.dumps({"x_post": long_x, "linkedin_post": "LinkedIn post " * 40})
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

    short_ln = json.dumps({"x_post": "Short X post here.", "linkedin_post": "Too short."})
    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response(short_ln)
    )
    with caplog.at_level(logging.WARNING, logger="app.integrations.anthropic_client"):
        await generate_social("brain dump", "Title", _VALID_BVP)
    assert any("500" in r.message or "below" in r.message for r in caplog.records)
