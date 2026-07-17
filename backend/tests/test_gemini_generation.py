"""Unit tests for the three new generation functions in integrations/gemini.py."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_response(text: str):
    mock_response = MagicMock()
    mock_response.text = text
    return mock_response


def _mock_aio_generate(response_text: str):
    """Return a mock _client.aio.models.generate_content coroutine."""
    return AsyncMock(return_value=_make_response(response_text))


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
    "<h2>Key Takeaways</h2><p>Conclusion text.</p>"
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


# ── generate_blog ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_returns_html(mock_client):
    from app.integrations.gemini import generate_blog

    mock_client.aio.models.generate_content = _mock_aio_generate(_VALID_BLOG_HTML)
    result = await generate_blog("My brain dump idea", _VALID_BVP)
    assert "<h1>" in result


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_strips_markdown_fences(mock_client):
    from app.integrations.gemini import generate_blog

    wrapped = f"```html\n{_VALID_BLOG_HTML}\n```"
    mock_client.aio.models.generate_content = _mock_aio_generate(wrapped)
    result = await generate_blog("idea", _VALID_BVP)
    assert not result.startswith("```")
    assert "<h1>" in result


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_uses_default_voice_when_bvp_is_none(mock_client):
    from app.integrations.gemini import generate_blog

    mock_client.aio.models.generate_content = _mock_aio_generate(_VALID_BLOG_HTML)
    result = await generate_blog("idea", None)
    assert "<h1>" in result
    assert mock_client.aio.models.generate_content.called


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_prompt_includes_mandatory_structure(mock_client):
    """Verify the new _BLOG_PROMPT template contains all required structural elements."""
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_BLOG_HTML)

    mock_client.aio.models.generate_content = capture
    await gemini.generate_blog("My brain dump", _VALID_BVP)

    prompt_text = captured_prompt[0]
    assert 'class="tldr"' in prompt_text
    assert "TL;DR:" in prompt_text
    assert "BLUF intro paragraph" in prompt_text
    assert 'class="faq"' in prompt_text
    assert "Frequently Asked Questions" in prompt_text
    assert "Key Takeaways" in prompt_text  # appears as a BANNED term, not as a mandatory heading
    assert "<h2>Key Takeaways</h2>" not in prompt_text
    assert "In Conclusion" in prompt_text or "in conclusion" in prompt_text  # appears in banned list
    assert "<!-- meta:" in prompt_text


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_prompt_includes_banned_phrase_list(mock_client):
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_BLOG_HTML)

    mock_client.aio.models.generate_content = capture
    await gemini.generate_blog("My brain dump", _VALID_BVP)

    prompt_text = captured_prompt[0]
    assert "In today's fast-paced world" in prompt_text
    assert "In today's digital landscape" in prompt_text
    assert "As we all know" in prompt_text
    assert "It's no secret that" in prompt_text
    assert "Now more than ever" in prompt_text
    assert "BANNED WORDS" in prompt_text
    assert "delve" in prompt_text


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_injects_seo_target_when_keyword_provided(mock_client):
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_BLOG_HTML)

    mock_client.aio.models.generate_content = capture
    await gemini.generate_blog("dump", _VALID_BVP, target_keyword="how to scale a SaaS app")

    prompt_text = captured_prompt[0]
    assert "SEO TARGET:" in prompt_text
    assert "how to scale a SaaS app" in prompt_text
    assert "SEARCH INTENT FOCUS" not in prompt_text


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_uses_search_intent_focus_when_no_keyword(mock_client):
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_BLOG_HTML)

    mock_client.aio.models.generate_content = capture
    await gemini.generate_blog("dump", _VALID_BVP)

    prompt_text = captured_prompt[0]
    assert "SEARCH INTENT FOCUS" in prompt_text
    assert "SEO TARGET:" not in prompt_text


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_includes_audience_section_when_provided(mock_client):
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_BLOG_HTML)

    mock_client.aio.models.generate_content = capture
    await gemini.generate_blog("dump", _VALID_BVP, target_audience="indie founders")

    prompt_text = captured_prompt[0]
    assert "TARGET AUDIENCE:" in prompt_text
    assert "indie founders" in prompt_text


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_omits_audience_section_when_not_provided(mock_client):
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_BLOG_HTML)

    mock_client.aio.models.generate_content = capture
    await gemini.generate_blog("dump", _VALID_BVP)

    prompt_text = captured_prompt[0]
    assert "TARGET AUDIENCE:" not in prompt_text


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_null_keyword_uses_search_intent_focus_not_seo_target(mock_client):
    """Regression: null keyword/audience → SEARCH INTENT FOCUS (not SEO TARGET:), no TARGET AUDIENCE:."""
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_BLOG_HTML)

    mock_client.aio.models.generate_content = capture
    await gemini.generate_blog("dump", _VALID_BVP, target_keyword=None, target_audience=None)

    prompt_text = captured_prompt[0]
    assert "SEO TARGET:" not in prompt_text
    assert "TARGET AUDIENCE:" not in prompt_text
    assert "SEARCH INTENT FOCUS" in prompt_text


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_injects_tldr_when_missing(mock_client):
    """If Gemini doesn't include TL;DR, it should be injected after </h1>."""
    from app.integrations.gemini import generate_blog

    html_no_tldr = "<h1>Test Title</h1><h2>S1</h2><p>body</p><h2>S2</h2><p>body2</p>"
    mock_client.aio.models.generate_content = _mock_aio_generate(html_no_tldr)
    result = await generate_blog("dump", _VALID_BVP)

    assert '<div class="tldr">' in result
    assert "TL;DR:" in result
    assert "[Summary pending review]" in result
    # Injected after </h1>
    h1_close = result.find("</h1>")
    tldr_pos = result.find('<div class="tldr">')
    assert tldr_pos == h1_close + len("</h1>")


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_does_not_inject_tldr_when_present(mock_client):
    """If Gemini already returned a TL;DR block, do not inject another."""
    from app.integrations.gemini import generate_blog

    mock_client.aio.models.generate_content = _mock_aio_generate(_VALID_BLOG_HTML)
    result = await generate_blog("dump", _VALID_BVP)
    assert result.count('<div class="tldr">') == 1


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_injects_tldr_when_h1_also_absent(mock_client):
    """TL;DR must be injected even when H1 is also missing (prepended to output)."""
    from app.integrations.gemini import generate_blog

    html_no_h1_no_tldr = "<h2>Section</h2><p>body</p><h2>Two</h2><p>b</p>"
    mock_client.aio.models.generate_content = _mock_aio_generate(html_no_h1_no_tldr)
    result = await generate_blog("dump", _VALID_BVP)

    assert '<div class="tldr">' in result
    assert "[Summary pending review]" in result
    assert result.startswith('<div class="tldr">')


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_injects_tldr_with_uppercase_h1_close_tag(mock_client):
    """TL;DR injection handles </H1> uppercase close tag correctly."""
    from app.integrations.gemini import generate_blog

    html_upper_h1 = "<H1>Test Title</H1><h2>S1</h2><p>body</p><h2>S2</h2><p>b</p>"
    mock_client.aio.models.generate_content = _mock_aio_generate(html_upper_h1)
    result = await generate_blog("dump", _VALID_BVP)

    assert '<div class="tldr">' in result
    assert result.count('<div class="tldr">') == 1


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_logs_warning_for_missing_h1(mock_client, caplog):
    from app.integrations.gemini import generate_blog
    import logging

    html_no_h1 = "<h2>Section</h2><p>body</p><h2>Two</h2><p>b</p>"
    mock_client.aio.models.generate_content = _mock_aio_generate(html_no_h1)
    with caplog.at_level(logging.WARNING, logger="app.integrations.gemini"):
        result = await generate_blog("dump", _VALID_BVP)
    assert any("H1" in r.message or "h1" in r.message.lower() for r in caplog.records)
    assert result  # does not raise


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_logs_warning_for_fewer_than_2_h2(mock_client, caplog):
    from app.integrations.gemini import generate_blog
    import logging

    html_one_h2 = "<h1>Title</h1><h2>Section</h2><p>body</p>"
    mock_client.aio.models.generate_content = _mock_aio_generate(html_one_h2)
    with caplog.at_level(logging.WARNING, logger="app.integrations.gemini"):
        result = await generate_blog("dump", _VALID_BVP)
    assert any("H2" in r.message or "h2" in r.message.lower() for r in caplog.records)
    assert result  # does not raise


# ── check_fidelity ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_check_fidelity_returns_7_key_scores(mock_client):
    from app.integrations.gemini import check_fidelity

    mock_client.aio.models.generate_content = _mock_aio_generate(_VALID_FIDELITY_JSON)
    result = await check_fidelity(_VALID_BLOG_HTML, _VALID_BVP)
    assert result["tone_score"] == 8
    assert result["cadence_score"] == 7
    assert result["jargon_violations"] == 0
    assert result["seo_bluf_present"] is True
    assert result["seo_h2_count"] == 4
    assert result["seo_faq_present"] is True
    assert result["seo_fluff_detected"] is False


@pytest.mark.asyncio
async def test_check_fidelity_returns_7_key_bypass_when_no_bvp():
    from app.integrations.gemini import check_fidelity

    result = await check_fidelity(_VALID_BLOG_HTML, None)
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


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_check_fidelity_raises_on_invalid_json(mock_client):
    from app.integrations.gemini import check_fidelity

    mock_client.aio.models.generate_content = _mock_aio_generate("not json")
    with pytest.raises(ValueError, match="invalid JSON"):
        await check_fidelity(_VALID_BLOG_HTML, _VALID_BVP)


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_check_fidelity_raises_on_missing_existing_key(mock_client):
    from app.integrations.gemini import check_fidelity

    bad = json.dumps({"tone_score": 8, "cadence_score": 7})  # missing jargon_violations
    mock_client.aio.models.generate_content = _mock_aio_generate(bad)
    with pytest.raises(ValueError, match="jargon_violations"):
        await check_fidelity(_VALID_BLOG_HTML, _VALID_BVP)


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_check_fidelity_raises_on_missing_seo_bool_key(mock_client):
    from app.integrations.gemini import check_fidelity

    # All 3 existing keys present but seo_bluf_present missing
    bad = json.dumps({
        "tone_score": 8, "cadence_score": 7, "jargon_violations": 0,
        "seo_h2_count": 3, "seo_faq_present": True, "seo_fluff_detected": False,
    })
    mock_client.aio.models.generate_content = _mock_aio_generate(bad)
    with pytest.raises(ValueError, match="seo_bluf_present"):
        await check_fidelity(_VALID_BLOG_HTML, _VALID_BVP)


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_check_fidelity_raises_on_wrong_bool_type(mock_client):
    from app.integrations.gemini import check_fidelity

    bad = json.dumps({
        "tone_score": 8, "cadence_score": 7, "jargon_violations": 0,
        "seo_bluf_present": "yes",  # should be bool
        "seo_h2_count": 3, "seo_faq_present": True, "seo_fluff_detected": False,
    })
    mock_client.aio.models.generate_content = _mock_aio_generate(bad)
    with pytest.raises(ValueError, match="seo_bluf_present.*bool"):
        await check_fidelity(_VALID_BLOG_HTML, _VALID_BVP)


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_check_fidelity_raises_on_non_int_h2_count(mock_client):
    from app.integrations.gemini import check_fidelity

    bad = json.dumps({
        "tone_score": 8, "cadence_score": 7, "jargon_violations": 0,
        "seo_bluf_present": True, "seo_h2_count": "3",  # should be int
        "seo_faq_present": True, "seo_fluff_detected": False,
    })
    mock_client.aio.models.generate_content = _mock_aio_generate(bad)
    with pytest.raises(ValueError, match="seo_h2_count.*int"):
        await check_fidelity(_VALID_BLOG_HTML, _VALID_BVP)


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_check_fidelity_raises_on_bool_h2_count(mock_client):
    """JSON true decodes as Python bool which is a subtype of int — must still be rejected."""
    from app.integrations.gemini import check_fidelity

    bad = json.dumps({
        "tone_score": 8, "cadence_score": 7, "jargon_violations": 0,
        "seo_bluf_present": True, "seo_h2_count": True,  # bool, not int
        "seo_faq_present": True, "seo_fluff_detected": False,
    })
    mock_client.aio.models.generate_content = _mock_aio_generate(bad)
    with pytest.raises(ValueError, match="seo_h2_count.*int"):
        await check_fidelity(_VALID_BLOG_HTML, _VALID_BVP)


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_check_fidelity_strips_markdown_fences(mock_client):
    from app.integrations.gemini import check_fidelity

    wrapped = f"```json\n{_VALID_FIDELITY_JSON}\n```"
    mock_client.aio.models.generate_content = _mock_aio_generate(wrapped)
    result = await check_fidelity(_VALID_BLOG_HTML, _VALID_BVP)
    assert "tone_score" in result
    assert "seo_bluf_present" in result


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_check_fidelity_returns_tags_when_present(mock_client):
    """Tags field is returned and sanitized (max 5, strings only)."""
    from app.integrations.gemini import check_fidelity

    payload = json.dumps({
        "tone_score": 8, "cadence_score": 7, "jargon_violations": 0,
        "seo_bluf_present": True, "seo_h2_count": 3, "seo_faq_present": True, "seo_fluff_detected": False,
        "tags": ["content marketing", "ai writing", "brand voice", "seo", "blogging", "extra"],
    })
    mock_client.aio.models.generate_content = _mock_aio_generate(payload)
    result = await check_fidelity(_VALID_BLOG_HTML, _VALID_BVP)
    assert result["tags"] == ["content marketing", "ai writing", "brand voice", "seo", "blogging"]


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_check_fidelity_tags_missing_is_ok(mock_client):
    """Tags field is optional — missing tags does not raise."""
    from app.integrations.gemini import check_fidelity

    payload = json.dumps({
        "tone_score": 8, "cadence_score": 7, "jargon_violations": 0,
        "seo_bluf_present": True, "seo_h2_count": 3, "seo_faq_present": True, "seo_fluff_detected": False,
    })
    mock_client.aio.models.generate_content = _mock_aio_generate(payload)
    result = await check_fidelity(_VALID_BLOG_HTML, _VALID_BVP)
    assert "tags" not in result


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_check_fidelity_tags_non_list_coerced_to_empty(mock_client):
    """If tags is not a list, it is coerced to [] instead of raising."""
    from app.integrations.gemini import check_fidelity

    payload = json.dumps({
        "tone_score": 8, "cadence_score": 7, "jargon_violations": 0,
        "seo_bluf_present": True, "seo_h2_count": 3, "seo_faq_present": True, "seo_fluff_detected": False,
        "tags": "not-a-list",
    })
    mock_client.aio.models.generate_content = _mock_aio_generate(payload)
    result = await check_fidelity(_VALID_BLOG_HTML, _VALID_BVP)
    assert result["tags"] == []


# ── extract_brand_voice ────────────────────────────────────────────────────────

_VALID_BVP_JSON = json.dumps({
    "tone": ["authoritative", "direct"],
    "cadence": {"avg_sentence_length": 18, "variation_pattern": "short", "paragraph_structure": "3-5 sentences"},
    "banned_jargon": ["leverage", "synergy"],
})

_VALID_BVP_WITH_AUDIENCE_JSON = json.dumps({
    "tone": ["authoritative", "direct"],
    "cadence": {"avg_sentence_length": 18, "variation_pattern": "short", "paragraph_structure": "3-5 sentences"},
    "banned_jargon": ["leverage", "synergy"],
    "target_audience": "Indie app developers building subscription products",
})

_VALID_BVP_WITH_NULL_AUDIENCE_JSON = json.dumps({
    "tone": ["authoritative", "direct"],
    "cadence": {"avg_sentence_length": 18, "variation_pattern": "short", "paragraph_structure": "3-5 sentences"},
    "banned_jargon": ["leverage", "synergy"],
    "target_audience": None,
})


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_extract_brand_voice_accepts_target_audience(mock_client):
    from app.integrations.gemini import extract_brand_voice

    mock_client.aio.models.generate_content = _mock_aio_generate(_VALID_BVP_WITH_AUDIENCE_JSON)
    result = await extract_brand_voice("sample website text")
    assert result["target_audience"] == "Indie app developers building subscription products"


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_extract_brand_voice_sets_none_when_target_audience_missing(mock_client):
    from app.integrations.gemini import extract_brand_voice

    mock_client.aio.models.generate_content = _mock_aio_generate(_VALID_BVP_JSON)
    result = await extract_brand_voice("sample website text")
    assert "target_audience" in result
    assert result["target_audience"] is None


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_extract_brand_voice_accepts_null_target_audience(mock_client):
    from app.integrations.gemini import extract_brand_voice

    mock_client.aio.models.generate_content = _mock_aio_generate(_VALID_BVP_WITH_NULL_AUDIENCE_JSON)
    result = await extract_brand_voice("sample website text")
    assert result["target_audience"] is None


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_extract_brand_voice_still_raises_on_missing_required_fields(mock_client):
    from app.integrations.gemini import extract_brand_voice

    bad = json.dumps({"tone": [], "cadence": {}})  # missing banned_jargon
    mock_client.aio.models.generate_content = _mock_aio_generate(bad)
    with pytest.raises(ValueError, match="banned_jargon"):
        await extract_brand_voice("sample text")


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_extract_brand_voice_bvp_prompt_includes_target_audience_field(mock_client):
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_BVP_WITH_AUDIENCE_JSON)

    mock_client.aio.models.generate_content = capture
    await gemini.extract_brand_voice("sample website text")

    prompt_text = captured_prompt[0]
    assert "target_audience" in prompt_text


# ── generate_social ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_social_returns_posts(mock_client):
    from app.integrations.gemini import generate_social

    mock_client.aio.models.generate_content = _mock_aio_generate(_VALID_SOCIAL_JSON)
    result = await generate_social("brain dump", "Test Title", _VALID_BVP)
    assert "x_post" in result
    assert "linkedin_post" in result


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_social_truncates_x_post_at_280(mock_client):
    from app.integrations.gemini import generate_social

    long_x = "x" * 300
    data = json.dumps({"x_post": long_x, "linkedin_post": "LinkedIn post " * 40})
    mock_client.aio.models.generate_content = _mock_aio_generate(data)
    result = await generate_social("brain dump", "Title", _VALID_BVP)
    assert len(result["x_post"]) == 280
    assert result["x_post"].endswith("…")


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_social_raises_on_invalid_json(mock_client):
    from app.integrations.gemini import generate_social

    mock_client.aio.models.generate_content = _mock_aio_generate("bad json")
    with pytest.raises(ValueError, match="invalid JSON"):
        await generate_social("brain dump", "Title", _VALID_BVP)


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_social_uses_default_voice_when_bvp_is_none(mock_client):
    from app.integrations.gemini import generate_social

    mock_client.aio.models.generate_content = _mock_aio_generate(_VALID_SOCIAL_JSON)
    result = await generate_social("brain dump", "Title", None)
    assert "x_post" in result


# ── Story 3-8: GEO & E-E-A-T prompt improvements ─────────────────────────────

@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_prompt_retains_eeat_signals(mock_client):
    """AC #1, #2: Brain dump label and REQUIREMENTS must retain E-E-A-T first-person signals."""
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_BLOG_HTML)

    mock_client.aio.models.generate_content = capture
    await gemini.generate_blog("I tested this and found conversion went from 1% to 3%", _VALID_BVP)

    prompt_text = captured_prompt[0]
    assert "first-person" in prompt_text.lower() or "E-E-A-T" in prompt_text


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_prompt_includes_information_gain_instruction(mock_client):
    """AC #3: REQUIREMENTS must include an Information Gain instruction."""
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_BLOG_HTML)

    mock_client.aio.models.generate_content = capture
    await gemini.generate_blog("My brain dump with proprietary data", _VALID_BVP)

    prompt_text = captured_prompt[0]
    assert "proprietary" in prompt_text.lower() or "Information Gain" in prompt_text


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_prompt_includes_geo_answer_block_rule(mock_client):
    """AC #4, #5: MANDATORY STRUCTURE must include the conditional GEO answer block rule."""
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_BLOG_HTML)

    mock_client.aio.models.generate_content = capture
    await gemini.generate_blog("My brain dump", _VALID_BVP)

    prompt_text = captured_prompt[0]
    assert "implies a direct question" in prompt_text.lower() or "AI Overview" in prompt_text


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_social_prompt_includes_linkedin_first_person_hook(mock_client):
    """AC #6: _SOCIAL_PROMPT must instruct Gemini to open LinkedIn posts with a first-person hook."""
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_SOCIAL_JSON)

    mock_client.aio.models.generate_content = capture
    await gemini.generate_social("My brain dump", "Test Title", _VALID_BVP)

    prompt_text = captured_prompt[0]
    assert "first-person" in prompt_text.lower()


# ── Story 3-10: Focus keyword rename + supporting keywords ────────────────────

def test_build_seo_section_includes_supporting_keywords_block():
    from app.integrations.gemini import _build_seo_section

    seo_section, _ = _build_seo_section("focus kw", None, "term1, term2")
    assert "SUPPORTING KEYWORDS" in seo_section
    assert "term1, term2" in seo_section


def test_build_seo_section_no_supporting_keywords_block_when_none():
    from app.integrations.gemini import _build_seo_section

    seo_section, _ = _build_seo_section("focus kw", None, None)
    assert "SUPPORTING KEYWORDS" not in seo_section


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_injects_supporting_keywords(mock_client):
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_BLOG_HTML)

    mock_client.aio.models.generate_content = capture
    await gemini.generate_blog("dump", _VALID_BVP, target_keyword="focus kw", secondary_keywords="term1, term2")

    prompt_text = captured_prompt[0]
    assert "SUPPORTING KEYWORDS" in prompt_text
    assert "term1, term2" in prompt_text


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_no_supporting_keywords_when_null(mock_client):
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_BLOG_HTML)

    mock_client.aio.models.generate_content = capture
    await gemini.generate_blog("dump", _VALID_BVP, target_keyword="focus kw", secondary_keywords=None)

    prompt_text = captured_prompt[0]
    assert "SUPPORTING KEYWORDS" not in prompt_text


# -- Story 3-11: Human content quality pass ──────────────────────────────────

@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_prompt_includes_burstiness_instruction(mock_client):
    """AC 1: REQUIREMENTS must instruct Gemini to vary sentence lengths dramatically."""
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_BLOG_HTML)

    mock_client.aio.models.generate_content = capture
    await gemini.generate_blog("My brain dump", _VALID_BVP)

    prompt_text = captured_prompt[0]
    assert "uniform sentence" in prompt_text.lower() or "3-8 words" in prompt_text


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_prompt_includes_section_structural_variation(mock_client):
    """AC 2: MANDATORY STRUCTURE must instruct Gemini to vary section structure."""
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_BLOG_HTML)

    mock_client.aio.models.generate_content = capture
    await gemini.generate_blog("My brain dump", _VALID_BVP)

    prompt_text = captured_prompt[0]
    assert "different structural approach" in prompt_text.lower() or "never use the same structure" in prompt_text.lower()


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_prompt_no_key_takeaways_as_mandatory_heading(mock_client):
    """AC 3: <h2>Key Takeaways</h2> must not appear as a mandatory structure element."""
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_BLOG_HTML)

    mock_client.aio.models.generate_content = capture
    await gemini.generate_blog("My brain dump", _VALID_BVP)

    prompt_text = captured_prompt[0]
    assert "<h2>Key Takeaways</h2>" not in prompt_text
    assert "Key Takeaways" in prompt_text  # still appears in the banned list


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_prompt_includes_intent_completion_rule(mock_client):
    """AC 4: REQUIREMENTS must include intent-completion rule (no unanswered follow-ups)."""
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_BLOG_HTML)

    mock_client.aio.models.generate_content = capture
    await gemini.generate_blog("My brain dump", _VALID_BVP)

    prompt_text = captured_prompt[0]
    assert "follow-up" in prompt_text.lower() or "open another tab" in prompt_text.lower()


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_prompt_applies_bvp_variation_pattern(mock_client):
    """AC 6: variation_pattern and paragraph_structure from BVP cadence must appear in the prompt."""
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_BLOG_HTML)

    mock_client.aio.models.generate_content = capture
    # _VALID_BVP has variation_pattern: "short" and paragraph_structure: "3-5 sentences"
    await gemini.generate_blog("My brain dump", _VALID_BVP)

    prompt_text = captured_prompt[0]
    assert 'sentence variation: "short"' in prompt_text   # variation_pattern value
    assert 'paragraph structure: "3-5 sentences"' in prompt_text  # paragraph_structure value


# ── Story 16.4: Voice-driven blog generation update ───────────────────────────

_VOICE_BRIEF = (
    "Boris writes in first person with punchy short sentences. "
    "He mixes casual contractions with specific numbers. "
    "His opening always hooks the reader immediately."
)

_BVP_WITH_VOICE_BRIEF = {
    "tone": ["direct", "casual"],
    "cadence": {"avg_sentence_length": 14, "variation_pattern": "punchy", "paragraph_structure": "short"},
    "banned_jargon": ["leverage"],
    "voice_brief": _VOICE_BRIEF,
    "list_preference": "rarely",
    "pronoun_preference": "first_person",
    "specificity_preference": "concrete_numbers",
    "closing_pattern": "cta",
    "header_style": "question",
}

_BVP_WITH_VOICE_BRIEF_NO_LIST_PREF = {
    **_BVP_WITH_VOICE_BRIEF,
    "list_preference": "normal",
}


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_voice_brief_present_in_prompt(mock_client):
    """AC 1: voice_brief text appears in the blog generation prompt when BVP has it."""
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_BLOG_HTML)

    mock_client.aio.models.generate_content = capture
    await gemini.generate_blog("My brain dump", _BVP_WITH_VOICE_BRIEF)

    prompt_text = captured_prompt[0]
    assert _VOICE_BRIEF in prompt_text
    assert "VOICE APPLICATION RULES" in prompt_text


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_voice_brief_meta_note_in_prompt(mock_client):
    """AC 3: condensed voice note appears in the meta description instruction when BVP has voice_brief."""
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_BLOG_HTML)

    mock_client.aio.models.generate_content = capture
    await gemini.generate_blog("My brain dump", _BVP_WITH_VOICE_BRIEF)

    prompt_text = captured_prompt[0]
    assert "write it in this voice:" in prompt_text
    # The meta line should include the voice note
    assert "<!-- meta:" in prompt_text
    meta_start = prompt_text.index("<!-- meta:")
    meta_end = prompt_text.index("-->", meta_start)
    meta_line = prompt_text[meta_start:meta_end]
    assert "write it in this voice:" in meta_line


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_no_voice_brief_uses_legacy_format(mock_client):
    """AC 6: when voice_brief is absent, prompt uses legacy JSON format with no empty sections."""
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_BLOG_HTML)

    mock_client.aio.models.generate_content = capture
    # _VALID_BVP has no voice_brief
    await gemini.generate_blog("My brain dump", _VALID_BVP)

    prompt_text = captured_prompt[0]
    # No voice injection sections should appear
    assert "VOICE APPLICATION RULES" not in prompt_text
    assert "write it in this voice:" not in prompt_text
    # Legacy BVP JSON should be in the prompt
    assert "authoritative" in prompt_text  # from tone field


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_list_rarely_inserts_no_bullet_rule(mock_client):
    """AC 1: list_preference='rarely' inserts the no-bullet-list rule."""
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_BLOG_HTML)

    mock_client.aio.models.generate_content = capture
    await gemini.generate_blog("My brain dump", _BVP_WITH_VOICE_BRIEF)

    prompt_text = captured_prompt[0]
    assert "Use NO bullet lists" in prompt_text


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_specificity_concrete_numbers_inserts_rule(mock_client):
    """AC 1: specificity_preference='concrete_numbers' inserts the numbers-required rule."""
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_BLOG_HTML)

    mock_client.aio.models.generate_content = capture
    await gemini.generate_blog("My brain dump", _BVP_WITH_VOICE_BRIEF)

    prompt_text = captured_prompt[0]
    assert "MUST use specific numbers" in prompt_text


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_social_linkedin_prompt_receives_voice_brief(mock_client):
    """AC 5: LinkedIn prompt receives voice_brief when BVP has it."""
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_SOCIAL_JSON)

    mock_client.aio.models.generate_content = capture
    await gemini.generate_social("brain dump", "Title", _BVP_WITH_VOICE_BRIEF)

    prompt_text = captured_prompt[0]
    assert _VOICE_BRIEF in prompt_text
    assert "LINKEDIN BRAND VOICE" in prompt_text


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_social_x_post_prompt_does_not_receive_voice_brief(mock_client):
    """AC 9: X post does NOT receive voice_brief -- it appears only in the LinkedIn section."""
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_SOCIAL_JSON)

    mock_client.aio.models.generate_content = capture
    await gemini.generate_social("brain dump", "Title", _BVP_WITH_VOICE_BRIEF)

    prompt_text = captured_prompt[0]
    # voice_brief appears only in the LINKEDIN BRAND VOICE section, not in the main bvp_json
    # (bvp_json strips voice_brief key so X post doesn't receive it in the core BRAND VOICE section)
    assert '"voice_brief"' not in prompt_text  # voice_brief key not serialized into bvp_json


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_list_normal_inserts_permissive_rule(mock_client):
    """list_preference other than 'rarely' produces the permissive list rule."""
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_BLOG_HTML)

    mock_client.aio.models.generate_content = capture
    await gemini.generate_blog("My brain dump", _BVP_WITH_VOICE_BRIEF_NO_LIST_PREF)

    prompt_text = captured_prompt[0]
    assert "Lists may appear where natural" in prompt_text
    assert "Use NO bullet lists" not in prompt_text


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_generate_blog_header_style_question_inserts_rule(mock_client):
    """header_style='question' inserts the H2/H3 phrased-as-questions rule."""
    from app.integrations import gemini

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_BLOG_HTML)

    mock_client.aio.models.generate_content = capture
    await gemini.generate_blog("My brain dump", _BVP_WITH_VOICE_BRIEF)

    prompt_text = captured_prompt[0]
    assert "phrased as questions" in prompt_text


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_check_fidelity_expanded_fields_returned_when_bvp_has_them(mock_client):
    """Advisory fields pronoun_score, specificity_score, closing_match are returned when BVP has them."""
    from app.integrations.gemini import check_fidelity

    fidelity_with_advisory = json.dumps({
        **json.loads(_VALID_FIDELITY_JSON),
        "pronoun_score": 8,
        "specificity_score": 9,
        "closing_match": True,
    })
    mock_client.aio.models.generate_content = _mock_aio_generate(fidelity_with_advisory)
    result = await check_fidelity(_VALID_BLOG_HTML, _BVP_WITH_VOICE_BRIEF)
    assert result["pronoun_score"] == 8
    assert result["specificity_score"] == 9
    assert result["closing_match"] is True


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_check_fidelity_advisory_fields_coerced_to_none_on_wrong_type(mock_client):
    """Invalid type for advisory fields is coerced to None without raising."""
    from app.integrations.gemini import check_fidelity

    fidelity_wrong_types = json.dumps({
        **json.loads(_VALID_FIDELITY_JSON),
        "pronoun_score": "nine",
        "specificity_score": "high",
        "closing_match": "yes",
    })
    mock_client.aio.models.generate_content = _mock_aio_generate(fidelity_wrong_types)
    result = await check_fidelity(_VALID_BLOG_HTML, _BVP_WITH_VOICE_BRIEF)
    assert result["pronoun_score"] is None
    assert result["specificity_score"] is None
    assert result["closing_match"] is None


@pytest.mark.asyncio
@patch("app.integrations.gemini._client")
async def test_check_fidelity_expanded_scoring_prompt_includes_advisory_instructions(mock_client):
    """When BVP has expanded fields, the prompt instructs Gemini to score pronoun, specificity, closing."""
    from app.integrations.gemini import check_fidelity

    captured_prompt = []

    async def capture(*args, **kwargs):
        captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
        return _make_response(_VALID_FIDELITY_JSON)

    mock_client.aio.models.generate_content = capture
    await check_fidelity(_VALID_BLOG_HTML, _BVP_WITH_VOICE_BRIEF)

    prompt_text = captured_prompt[0]
    assert "pronoun_score" in prompt_text
    assert "first_person" in prompt_text
    assert "specificity_score" in prompt_text
    assert "closing_match" in prompt_text
