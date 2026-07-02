"""Unit tests for the three new generation functions in integrations/gemini.py."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_gemini_model(response_text: str):
    mock_response = MagicMock()
    mock_response.text = response_text
    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(return_value=mock_response)
    return mock_model


_VALID_BVP = {
    "tone": ["authoritative", "direct"],
    "cadence": {"avg_sentence_length": 18, "variation_pattern": "short", "paragraph_structure": "3-5 sentences"},
    "banned_jargon": ["leverage", "synergy"],
}

_VALID_BLOG_HTML = "<h1>Test Title</h1><h2>Section</h2><p>Body paragraph.</p>"

_VALID_FIDELITY_JSON = json.dumps({"tone_score": 8, "cadence_score": 7, "jargon_violations": 0})

_VALID_SOCIAL_JSON = json.dumps({
    "x_post": "Check out this blog post about testing!",
    "linkedin_post": "We published a new article. " * 25,  # ~625 chars
})


# ── generate_blog ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.integrations.gemini.genai")
async def test_generate_blog_returns_html(mock_genai):
    from app.integrations.gemini import generate_blog

    mock_genai.GenerativeModel.return_value = _mock_gemini_model(_VALID_BLOG_HTML)
    result = await generate_blog("My brain dump idea", _VALID_BVP)
    assert "<h1>" in result


@pytest.mark.asyncio
@patch("app.integrations.gemini.genai")
async def test_generate_blog_uses_thinking_budget(mock_genai):
    from app.integrations.gemini import generate_blog

    mock_genai.GenerativeModel.return_value = _mock_gemini_model(_VALID_BLOG_HTML)
    await generate_blog("idea", _VALID_BVP, thinking_tokens=512)
    call_kwargs = mock_genai.GenerativeModel.call_args
    generation_config = call_kwargs[1].get("generation_config") or call_kwargs[0][1]
    assert generation_config.get("thinking_budget") == 512


@pytest.mark.asyncio
@patch("app.integrations.gemini.genai")
async def test_generate_blog_strips_markdown_fences(mock_genai):
    from app.integrations.gemini import generate_blog

    wrapped = f"```html\n{_VALID_BLOG_HTML}\n```"
    mock_genai.GenerativeModel.return_value = _mock_gemini_model(wrapped)
    result = await generate_blog("idea", _VALID_BVP)
    assert not result.startswith("```")
    assert "<h1>" in result


@pytest.mark.asyncio
@patch("app.integrations.gemini.genai")
async def test_generate_blog_uses_default_voice_when_bvp_is_none(mock_genai):
    from app.integrations.gemini import generate_blog

    mock_genai.GenerativeModel.return_value = _mock_gemini_model(_VALID_BLOG_HTML)
    result = await generate_blog("idea", None)
    assert "<h1>" in result
    # Verify prompt was constructed (model was called)
    assert mock_genai.GenerativeModel.return_value.generate_content_async.called


# ── check_fidelity ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.integrations.gemini.genai")
async def test_check_fidelity_returns_scores(mock_genai):
    from app.integrations.gemini import check_fidelity

    mock_genai.GenerativeModel.return_value = _mock_gemini_model(_VALID_FIDELITY_JSON)
    result = await check_fidelity(_VALID_BLOG_HTML, _VALID_BVP)
    assert result["tone_score"] == 8
    assert result["cadence_score"] == 7
    assert result["jargon_violations"] == 0


@pytest.mark.asyncio
async def test_check_fidelity_returns_perfect_score_when_no_bvp():
    from app.integrations.gemini import check_fidelity

    result = await check_fidelity(_VALID_BLOG_HTML, None)
    assert result == {"tone_score": 10, "cadence_score": 10, "jargon_violations": 0}


@pytest.mark.asyncio
@patch("app.integrations.gemini.genai")
async def test_check_fidelity_raises_on_invalid_json(mock_genai):
    from app.integrations.gemini import check_fidelity

    mock_genai.GenerativeModel.return_value = _mock_gemini_model("not json")
    with pytest.raises(ValueError, match="invalid JSON"):
        await check_fidelity(_VALID_BLOG_HTML, _VALID_BVP)


@pytest.mark.asyncio
@patch("app.integrations.gemini.genai")
async def test_check_fidelity_raises_on_missing_key(mock_genai):
    from app.integrations.gemini import check_fidelity

    bad = json.dumps({"tone_score": 8, "cadence_score": 7})  # missing jargon_violations
    mock_genai.GenerativeModel.return_value = _mock_gemini_model(bad)
    with pytest.raises(ValueError, match="jargon_violations"):
        await check_fidelity(_VALID_BLOG_HTML, _VALID_BVP)


@pytest.mark.asyncio
@patch("app.integrations.gemini.genai")
async def test_check_fidelity_strips_markdown_fences(mock_genai):
    from app.integrations.gemini import check_fidelity

    wrapped = f"```json\n{_VALID_FIDELITY_JSON}\n```"
    mock_genai.GenerativeModel.return_value = _mock_gemini_model(wrapped)
    result = await check_fidelity(_VALID_BLOG_HTML, _VALID_BVP)
    assert "tone_score" in result


# ── generate_social ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.integrations.gemini.genai")
async def test_generate_social_returns_posts(mock_genai):
    from app.integrations.gemini import generate_social

    mock_genai.GenerativeModel.return_value = _mock_gemini_model(_VALID_SOCIAL_JSON)
    result = await generate_social("brain dump", "Test Title", _VALID_BVP)
    assert "x_post" in result
    assert "linkedin_post" in result


@pytest.mark.asyncio
@patch("app.integrations.gemini.genai")
async def test_generate_social_uses_zero_thinking_tokens(mock_genai):
    from app.integrations.gemini import generate_social

    mock_genai.GenerativeModel.return_value = _mock_gemini_model(_VALID_SOCIAL_JSON)
    await generate_social("brain dump", "Title", _VALID_BVP, thinking_tokens=0)
    call_kwargs = mock_genai.GenerativeModel.call_args
    generation_config = call_kwargs[1].get("generation_config") or call_kwargs[0][1]
    assert generation_config.get("thinking_budget") == 0


@pytest.mark.asyncio
@patch("app.integrations.gemini.genai")
async def test_generate_social_truncates_x_post_at_280(mock_genai):
    from app.integrations.gemini import generate_social

    long_x = "x" * 300
    data = json.dumps({"x_post": long_x, "linkedin_post": "LinkedIn post " * 40})
    mock_genai.GenerativeModel.return_value = _mock_gemini_model(data)
    result = await generate_social("brain dump", "Title", _VALID_BVP)
    assert len(result["x_post"]) == 280
    assert result["x_post"].endswith("…")


@pytest.mark.asyncio
@patch("app.integrations.gemini.genai")
async def test_generate_social_raises_on_invalid_json(mock_genai):
    from app.integrations.gemini import generate_social

    mock_genai.GenerativeModel.return_value = _mock_gemini_model("bad json")
    with pytest.raises(ValueError, match="invalid JSON"):
        await generate_social("brain dump", "Title", _VALID_BVP)


@pytest.mark.asyncio
@patch("app.integrations.gemini.genai")
async def test_generate_social_strips_markdown_fences(mock_genai):
    from app.integrations.gemini import generate_social

    wrapped = f"```json\n{_VALID_SOCIAL_JSON}\n```"
    mock_genai.GenerativeModel.return_value = _mock_gemini_model(wrapped)
    result = await generate_social("brain dump", "Title", _VALID_BVP)
    assert "x_post" in result


@pytest.mark.asyncio
@patch("app.integrations.gemini.genai")
async def test_generate_social_uses_default_voice_when_bvp_is_none(mock_genai):
    from app.integrations.gemini import generate_social

    mock_genai.GenerativeModel.return_value = _mock_gemini_model(_VALID_SOCIAL_JSON)
    result = await generate_social("brain dump", "Title", None)
    assert "x_post" in result
