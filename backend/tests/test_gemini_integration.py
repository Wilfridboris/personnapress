"""Unit tests for integrations/gemini.py — extract_brand_voice()."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_gemini_model(response_text: str):
    """Return a mock GenerativeModel whose generate_content_async returns response_text."""
    mock_response = MagicMock()
    mock_response.text = response_text

    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(return_value=mock_response)
    return mock_model


_VALID_BVP_JSON = json.dumps({
    "tone": ["authoritative", "direct"],
    "cadence": {
        "avg_sentence_length": 18,
        "variation_pattern": "short punchy sentences",
        "paragraph_structure": "3-5 sentences, opens with a claim",
    },
    "banned_jargon": ["leverage", "synergy"],
})


# ── Happy path ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.integrations.gemini.genai")
async def test_extract_brand_voice_returns_dict(mock_genai):
    from app.integrations.gemini import extract_brand_voice

    mock_genai.GenerativeModel.return_value = _mock_gemini_model(_VALID_BVP_JSON)

    result = await extract_brand_voice("Some brand text", thinking_tokens=1024)

    assert isinstance(result, dict)
    assert result["tone"] == ["authoritative", "direct"]
    assert result["cadence"]["avg_sentence_length"] == 18
    assert "leverage" in result["banned_jargon"]


@pytest.mark.asyncio
@patch("app.integrations.gemini.genai")
async def test_extract_brand_voice_strips_markdown_fences(mock_genai):
    from app.integrations.gemini import extract_brand_voice

    # Simulate model wrapping JSON in ```json ... ``` code fences
    wrapped = f"```json\n{_VALID_BVP_JSON}\n```"
    mock_genai.GenerativeModel.return_value = _mock_gemini_model(wrapped)

    result = await extract_brand_voice("Some text")

    assert isinstance(result, dict)
    assert isinstance(result["tone"], list)


@pytest.mark.asyncio
@patch("app.integrations.gemini.genai")
async def test_extract_brand_voice_uses_thinking_budget(mock_genai):
    """GenerativeModel must be instantiated with thinking_budget in generation_config."""
    from app.integrations.gemini import extract_brand_voice

    mock_genai.GenerativeModel.return_value = _mock_gemini_model(_VALID_BVP_JSON)

    await extract_brand_voice("Text", thinking_tokens=1024)

    call_kwargs = mock_genai.GenerativeModel.call_args
    generation_config = call_kwargs[1].get("generation_config") or call_kwargs[0][1]
    assert generation_config.get("thinking_budget") == 1024


# ── Validation errors ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.integrations.gemini.genai")
async def test_extract_brand_voice_invalid_json_raises_value_error(mock_genai):
    from app.integrations.gemini import extract_brand_voice

    mock_genai.GenerativeModel.return_value = _mock_gemini_model("not valid json at all")

    with pytest.raises(ValueError, match="invalid JSON"):
        await extract_brand_voice("Some text")


@pytest.mark.asyncio
@patch("app.integrations.gemini.genai")
async def test_extract_brand_voice_missing_tone_raises_value_error(mock_genai):
    from app.integrations.gemini import extract_brand_voice

    bad_json = json.dumps({
        "cadence": {"avg_sentence_length": 18, "variation_pattern": "x", "paragraph_structure": "y"},
        "banned_jargon": [],
    })
    mock_genai.GenerativeModel.return_value = _mock_gemini_model(bad_json)

    with pytest.raises(ValueError, match="tone"):
        await extract_brand_voice("Some text")


@pytest.mark.asyncio
@patch("app.integrations.gemini.genai")
async def test_extract_brand_voice_missing_cadence_raises_value_error(mock_genai):
    from app.integrations.gemini import extract_brand_voice

    bad_json = json.dumps({
        "tone": ["direct"],
        "banned_jargon": [],
    })
    mock_genai.GenerativeModel.return_value = _mock_gemini_model(bad_json)

    with pytest.raises(ValueError, match="cadence"):
        await extract_brand_voice("Some text")


@pytest.mark.asyncio
@patch("app.integrations.gemini.genai")
async def test_extract_brand_voice_tone_not_list_raises_value_error(mock_genai):
    from app.integrations.gemini import extract_brand_voice

    bad_json = json.dumps({
        "tone": "should be a list",
        "cadence": {"avg_sentence_length": 10, "variation_pattern": "", "paragraph_structure": ""},
        "banned_jargon": [],
    })
    mock_genai.GenerativeModel.return_value = _mock_gemini_model(bad_json)

    with pytest.raises(ValueError, match="tone"):
        await extract_brand_voice("Some text")


# ── Gap-fill: banned_jargon validation ───────────────────────────────────────

@pytest.mark.asyncio
@patch("app.integrations.gemini.genai")
async def test_extract_brand_voice_banned_jargon_not_list_raises_value_error(mock_genai):
    """banned_jargon must be a list; a string value raises ValueError."""
    from app.integrations.gemini import extract_brand_voice

    bad_json = json.dumps({
        "tone": ["direct"],
        "cadence": {"avg_sentence_length": 10, "variation_pattern": "", "paragraph_structure": ""},
        "banned_jargon": "should be a list not a string",
    })
    mock_genai.GenerativeModel.return_value = _mock_gemini_model(bad_json)

    with pytest.raises(ValueError, match="banned_jargon"):
        await extract_brand_voice("Some text")


# ── Gap-fill: 50 k character text cap ────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.integrations.gemini.genai")
async def test_extract_brand_voice_truncates_text_at_50k_chars(mock_genai):
    """Text longer than 50 000 chars is truncated before being sent to Gemini."""
    from app.integrations.gemini import extract_brand_voice

    mock_model = _mock_gemini_model(_VALID_BVP_JSON)
    mock_genai.GenerativeModel.return_value = mock_model

    long_text = "a" * 100_000
    await extract_brand_voice(long_text)

    call_args = mock_model.generate_content_async.call_args
    prompt_sent: str = call_args[0][0]
    # The prompt embeds the text slice; 50 001 identical chars must NOT appear
    assert "a" * 50_001 not in prompt_sent
    assert "a" * 50_000 in prompt_sent
