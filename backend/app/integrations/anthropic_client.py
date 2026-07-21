"""Anthropic LLM integration for content generation.

Called ONLY from services/generation.py (AR-19).
Implements same 3 function signatures as integrations/gemini.py generation functions.
BVP ingestion (extract_brand_voice, synthesize_voice_brief) always uses Gemini -- not here.
"""

import json
import logging
import re

import anthropic

from app.core.config import settings
from app.integrations.generation_prompts import (
    _DEFAULT_VOICE,
    _BLOG_PROMPT,
    _FIDELITY_PROMPT,
    _SOCIAL_PROMPT,
    _build_seo_section,
    _build_voice_injection,
    _meta_voice_note,
    _strip_fences,
    _md_to_html,
)

logger = logging.getLogger(__name__)

# max_retries=0: disable SDK's built-in auto-retry so _llm_with_retry in generation.py
# has sole control over the backoff strategy (avoid double-retry).
_client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY, max_retries=0)
_MODEL = settings.ANTHROPIC_MODEL
logger.info("Anthropic model: %s", _MODEL)


async def _call(prompt: str, max_tokens: int) -> str:
    """Standard call -- no thinking. Safe to use response.content[0].text."""
    response = await _client.messages.create(
        model=_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    if not response.content:
        raise ValueError("_call: Anthropic response content is empty")
    return response.content[0].text


async def _call_with_thinking(prompt: str, max_tokens: int, budget_tokens: int) -> str:
    """Call with extended thinking. response.content[0] may be a ThinkingBlock."""
    response = await _client.messages.create(
        model=_MODEL,
        max_tokens=max_tokens,
        thinking={"type": "enabled", "budget_tokens": budget_tokens},
        messages=[{"role": "user", "content": prompt}],
        extra_headers={"anthropic-beta": "interleaved-thinking-2025-05-14"},
    )
    text = next((b.text for b in response.content if b.type == "text"), None)
    if text is None:
        raise ValueError("_call_with_thinking: Anthropic response contains no text block")
    return text


async def generate_blog(
    brain_dump: str,
    brand_voice_profile: dict | None,
    thinking_tokens: int = 512,
    target_keyword: str | None = None,
    target_audience: str | None = None,
    secondary_keywords: str | None = None,
) -> str:
    if brand_voice_profile:
        tone_list = ", ".join(str(t) for t in brand_voice_profile.get("tone", []))
        cadence = brand_voice_profile.get("cadence") or {}
        avg_sentence_length = cadence.get("avg_sentence_length") or 15
        variation_pattern = str(cadence.get("variation_pattern") or "").strip()
        paragraph_structure = str(cadence.get("paragraph_structure") or "").strip()
        cadence_parts = [f"avg sentence length {avg_sentence_length} words"]
        if variation_pattern:
            cadence_parts.append(f'sentence variation: "{variation_pattern}"')
        if paragraph_structure:
            cadence_parts.append(f'paragraph structure: "{paragraph_structure}"')
        cadence_instruction = "; ".join(cadence_parts)
        if variation_pattern or paragraph_structure:
            cadence_instruction += ". Apply all of these patterns literally in the prose."
        banned_jargon_list = ", ".join(str(j) for j in brand_voice_profile.get("banned_jargon", []))
        if brand_voice_profile.get("voice_brief"):
            voice_section = _build_voice_injection(brand_voice_profile)
        else:
            voice_section = json.dumps(brand_voice_profile)
    else:
        voice_section = _DEFAULT_VOICE
        tone_list = "professional, clear, authoritative"
        cadence_instruction = "avg sentence length 15 words"
        banned_jargon_list = "none specified"

    meta_voice_note = _meta_voice_note(brand_voice_profile or {})
    seo_target_section, audience_section = _build_seo_section(target_keyword, target_audience, secondary_keywords)

    prompt = _BLOG_PROMPT.format(
        voice_section=voice_section,
        meta_voice_note=meta_voice_note,
        brain_dump=brain_dump,
        tone_list=tone_list,
        cadence_instruction=cadence_instruction,
        banned_jargon_list=banned_jargon_list,
        seo_target_section=seo_target_section,
        audience_section=audience_section,
    )

    max_tokens = max(8192, thinking_tokens + 4096)
    if thinking_tokens > 0:
        raw = await _call_with_thinking(prompt, max_tokens, thinking_tokens)
    else:
        raw = await _call(prompt, max_tokens)

    result = _md_to_html(_strip_fences(raw.strip()))
    result = result.replace("—", ", ")

    if "<h1" not in result.lower():
        logger.warning("generate_blog: Anthropic output missing H1 tag")
    h2_count = result.lower().count("<h2")
    if h2_count < 2:
        logger.warning("generate_blog: Anthropic output has fewer than 2 H2 tags (%d found)", h2_count)
    if '<div class="tldr">' not in result:
        h1_close = result.lower().find("</h1>")
        if h1_close != -1:
            insert_pos = h1_close + len("</h1>")
            result = (
                result[:insert_pos]
                + '<div class="tldr"><p><strong>TL;DR:</strong> [Summary pending review]</p></div>'
                + result[insert_pos:]
            )
        else:
            result = (
                '<div class="tldr"><p><strong>TL;DR:</strong> [Summary pending review]</p></div>'
                + result
            )

    return result


async def check_fidelity(
    blog_html: str,
    brand_voice_profile: dict | None,
    thinking_tokens: int = 256,    # unused -- no thinking on fidelity check
) -> dict:
    if brand_voice_profile is None:
        return {
            "tone_score": 10,
            "cadence_score": 10,
            "jargon_violations": 0,
            "seo_bluf_present": True,
            "seo_h2_count": 3,
            "seo_faq_present": True,
            "seo_fluff_detected": False,
            "tags": [],
        }

    bvp = brand_voice_profile
    expanded_parts: list[str] = []
    if bvp.get("pronoun_preference"):
        pronoun = bvp["pronoun_preference"]
        expanded_parts.append(
            f'  "pronoun_score": <integer 0-10, how consistently does the post use {pronoun} pronouns?>'
        )
    if bvp.get("specificity_preference"):
        spec_pref = bvp["specificity_preference"]
        expanded_parts.append(
            f'  "specificity_score": <integer 0-10, how well does the post match the "{spec_pref}" specificity preference?>'
        )
    if bvp.get("closing_pattern"):
        closing = bvp["closing_pattern"]
        expanded_parts.append(
            f'  "closing_match": <boolean, does the conclusion match the expected "{closing}" closing pattern?>'
        )

    if expanded_parts:
        expanded_scoring_section = (
            "\nAlso add these advisory fields to the JSON object above:\n"
            + "\n".join(expanded_parts)
        )
    else:
        expanded_scoring_section = ""

    prompt = _FIDELITY_PROMPT.format(
        bvp_json=json.dumps(brand_voice_profile),
        blog_html=blog_html,
        expanded_scoring_section=expanded_scoring_section,
    )

    raw = _strip_fences((await _call(prompt, max_tokens=1024)).strip())

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("check_fidelity: Anthropic returned invalid JSON: %r", raw[:200])
        raise ValueError(f"check_fidelity: Anthropic returned invalid JSON: {exc}") from exc

    for key in ("tone_score", "cadence_score", "jargon_violations"):
        if key not in data:
            raise ValueError(f"check_fidelity: missing key '{key}' in Anthropic response")
        if not isinstance(data[key], (int, float)):
            raise ValueError(
                f"check_fidelity: '{key}' must be numeric, got {type(data[key]).__name__}"
            )

    seo_bool_keys = ("seo_bluf_present", "seo_faq_present", "seo_fluff_detected")
    for key in seo_bool_keys:
        if key not in data:
            raise ValueError(f"check_fidelity: missing key '{key}' in Anthropic response")
        if not isinstance(data[key], bool):
            raise ValueError(
                f"check_fidelity: '{key}' must be bool, got {type(data[key]).__name__}"
            )
    if "seo_h2_count" not in data:
        raise ValueError("check_fidelity: missing key 'seo_h2_count' in Anthropic response")
    if not isinstance(data["seo_h2_count"], int) or isinstance(data["seo_h2_count"], bool):
        raise ValueError(
            f"check_fidelity: 'seo_h2_count' must be int, got {type(data['seo_h2_count']).__name__}"
        )

    if "tags" in data:
        if not isinstance(data["tags"], list):
            logger.warning("check_fidelity: 'tags' is not a list (got %s), coercing to []", type(data["tags"]).__name__)
            data["tags"] = []
        else:
            data["tags"] = [
                re.sub(r"[\r\n]", " ", t).strip()
                for t in data["tags"]
                if isinstance(t, str)
            ][:5]

    for advisory_key in ("pronoun_score", "specificity_score"):
        if advisory_key in data and not isinstance(data[advisory_key], (int, float)):
            data[advisory_key] = None
    if "closing_match" in data and not isinstance(data["closing_match"], bool):
        data["closing_match"] = None

    return data


async def generate_social(
    brain_dump: str,
    blog_title: str,
    brand_voice_profile: dict | None,
    thinking_tokens: int = 0,    # unused -- no thinking on social posts
) -> dict:
    if brand_voice_profile:
        bvp_without_voice = {k: v for k, v in brand_voice_profile.items() if k != "voice_brief"}
        bvp_json = json.dumps(bvp_without_voice)
    else:
        bvp_json = _DEFAULT_VOICE

    voice_brief = (brand_voice_profile or {}).get("voice_brief") or ""
    if voice_brief:
        linkedin_voice_section = (
            "\nLINKEDIN BRAND VOICE (apply to linkedin_post only -- do not apply to x_post):\n"
            f"{voice_brief}\n"
        )
    else:
        linkedin_voice_section = ""

    prompt = _SOCIAL_PROMPT.format(
        bvp_json=bvp_json,
        linkedin_voice_section=linkedin_voice_section,
        brain_dump=brain_dump,
        blog_title=blog_title,
    )

    raw = _strip_fences((await _call(prompt, max_tokens=1024)).strip())

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("generate_social: Anthropic returned invalid JSON: %r", raw[:200])
        raise ValueError(f"generate_social: Anthropic returned invalid JSON: {exc}") from exc

    for key in ("x_post", "linkedin_post"):
        if key not in data:
            raise ValueError(f"generate_social: missing key '{key}' in Anthropic response")
        if not isinstance(data[key], str):
            raise ValueError(
                f"generate_social: '{key}' must be a string, got {type(data[key]).__name__}"
            )

    if len(data["x_post"]) > 280:
        logger.warning(
            "generate_social: X post exceeded 280 chars (%d), truncating",
            len(data["x_post"]),
        )
        data["x_post"] = data["x_post"][:279] + "…"

    ln_len = len(data["linkedin_post"])
    if ln_len > 1300:
        logger.warning(
            "generate_social: LinkedIn post exceeded 1300 chars (%d), truncating",
            ln_len,
        )
        data["linkedin_post"] = data["linkedin_post"][:1299] + "…"
    elif ln_len < 500:
        logger.warning(
            "generate_social: LinkedIn post length %d is below expected 500 chars",
            ln_len,
        )

    return data
