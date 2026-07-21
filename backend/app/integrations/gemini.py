"""Gemini LLM integration.

Called ONLY from services/ingestion.py and services/generation.py (AR-19).
Do not call this module directly from routers or workers.
"""

import json
import logging
import re

from google import genai
from google.genai import types

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

_client = genai.Client(api_key=settings.GEMINI_API_KEY)

_MODEL = settings.GEMINI_MODEL
logger.info("Gemini model: %s", _MODEL)

_BVP_PROMPT_TEMPLATE = """Analyze the following text and extract a Brand Voice Profile.

Return ONLY a valid JSON object with this exact schema. No markdown code blocks, no explanation. Raw JSON only.

{{
  "tone": ["list", "of", "style", "descriptors"],
  "cadence": {{
    "avg_sentence_length": <integer>,
    "variation_pattern": "<string>",
    "paragraph_structure": "<string>"
  }},
  "banned_jargon": ["words", "or", "phrases", "to", "avoid"],
  "target_audience": "<one sentence describing who this brand writes for, inferred from the content, or null if unclear>",

  "pronoun_preference": "<first_person | second_person | mixed>",
  "formality_scale": <integer 1-5, where 1 = very casual and 5 = very formal>,
  "humor_style": "<none | dry | playful | self_deprecating>",
  "vocabulary_complexity": "<plain | mixed | technical>",

  "example_style": "<analogy | data | story | direct>",
  "specificity_preference": "<concrete_numbers | vague_quantifiers | mixed>",
  "opening_pattern": "<question | bold_claim | anecdote | stat | problem>",
  "closing_pattern": "<cta | question | summary | one_liner | none>",
  "header_style": "<question | command | statement | mixed>",
  "post_structure_template": "<free text, e.g. hook -- pain -- insight -- example -- CTA>",

  "signature_phrases": ["5 to 10 short phrases pulled verbatim from the samples"],
  "voice_anchor_sentences": ["3 to 5 complete sentences pulled verbatim that best represent the voice"],
  "anti_pattern_example": "<one sentence this writer would never produce>"
}}

Field definitions:
- pronoun_preference: how the author typically refers to themselves (first_person), the reader (second_person), or both (mixed)
- formality_scale: 1 (very casual, contractions and slang) to 5 (very formal, no contractions, academic register)
- humor_style: none if absent, or the predominant style of humor detected
- vocabulary_complexity: plain (everyday words), mixed, or technical (domain-specific terminology)
- example_style: the most common way this author illustrates a point
- specificity_preference: whether the author uses concrete data and numbers or vague quantifiers
- opening_pattern: how the author typically begins a post or article
- closing_pattern: how the author typically ends a post or article
- header_style: the pattern used for section headings
- post_structure_template: the typical skeleton for a post, described as a flow in plain text
- signature_phrases: repeated or distinctive short phrases pulled verbatim; aim for 5-10 items
- voice_anchor_sentences: 3 to 5 verbatim sentences that best capture the voice
- anti_pattern_example: one sentence that sounds nothing like this writer

TEXT TO ANALYZE:
{text}"""


_QUALITATIVE_DEFAULTS: dict = {
    "pronoun_preference": "mixed",
    "formality_scale": 3,
    "humor_style": "none",
    "vocabulary_complexity": "plain",
    "example_style": "direct",
    "specificity_preference": "mixed",
    "opening_pattern": "bold_claim",
    "closing_pattern": "none",
    "header_style": "statement",
    "post_structure_template": "",
    "signature_phrases": [],
    "voice_anchor_sentences": [],
    "anti_pattern_example": "",
}

_VOICE_BRIEF_PROMPT = """You are analyzing a Brand Voice Profile JSON and writing a third-person voice brief.

BRAND VOICE PROFILE:
{bvp_json}

Write a plain prose paragraph of 150-250 words describing how this person writes.
Cover: pronoun choice, formality, sentence rhythm, how they open and close posts,
how they use examples, their vocabulary complexity, and what makes their writing distinctive.
Do NOT use JSON, field names, or bullet points. Write in flowing prose.
Do NOT use em-dashes. Use plain dashes (--) or restructure the sentence instead.
Return ONLY the paragraph. No heading, no explanation."""


def _thinking_config(thinking_tokens: int) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=thinking_tokens)
    )


async def synthesize_voice_brief(bvp: dict, thinking_tokens: int = 256) -> str:
    prompt = _VOICE_BRIEF_PROMPT.format(bvp_json=json.dumps(bvp, indent=2))
    try:
        response = await _client.aio.models.generate_content(
            model=_MODEL,
            contents=prompt,
            config=_thinking_config(thinking_tokens),
        )
        text = response.text.strip()
        return text if text else ""
    except Exception:
        logger.exception("Voice brief synthesis failed")
        return ""


async def extract_brand_voice(text: str, thinking_tokens: int = 1024) -> dict:
    prompt = _BVP_PROMPT_TEMPLATE.format(text=text[:50_000])

    response = await _client.aio.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=_thinking_config(thinking_tokens),
    )

    raw = response.text.strip()

    if raw.startswith("```"):
        parts = raw.split("```")
        inner = parts[1]
        if inner.startswith("json"):
            inner = inner[4:]
        raw = inner.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Gemini returned invalid JSON: %r", raw[:200])
        raise ValueError(f"Gemini returned invalid JSON: {exc}") from exc

    if not isinstance(data.get("tone"), list):
        raise ValueError("Gemini BVP missing or invalid 'tone' field")
    if not isinstance(data.get("cadence"), dict):
        raise ValueError("Gemini BVP missing or invalid 'cadence' field")
    if not isinstance(data.get("banned_jargon"), list):
        raise ValueError("Gemini BVP missing or invalid 'banned_jargon' field")

    # Soft check: target_audience is optional
    if "target_audience" not in data:
        data["target_audience"] = None
    elif data["target_audience"] is not None and not isinstance(data["target_audience"], str):
        data["target_audience"] = None  # coerce invalid type to None silently

    for key, default in _QUALITATIVE_DEFAULTS.items():
        if key not in data or data[key] is None:
            data[key] = default

    # Synthesize from qualitative fields only; ingestion.py re-synthesizes after
    # merging computed stylometric fields and existing BVP arrays (AC 3 / AC 8).
    data["voice_brief"] = await synthesize_voice_brief(data)

    return data


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
        # Use voice injection when voice_brief is present; fall back to JSON for legacy BVPs
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

    response = await _client.aio.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=_thinking_config(thinking_tokens),
    )
    result = _md_to_html(_strip_fences(response.text.strip()))
    # Belt-and-suspenders: replace any em-dashes the model emitted despite the ban
    result = result.replace("—", ", ")

    # Post-processing validation pass
    if "<h1" not in result.lower():
        logger.warning("generate_blog: Gemini output missing H1 tag")
    h2_count = result.lower().count("<h2")
    if h2_count < 2:
        logger.warning("generate_blog: Gemini output has fewer than 2 H2 tags (%d found)", h2_count)
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
            # H1 also absent: prepend TL;DR so the block is never omitted
            result = (
                '<div class="tldr"><p><strong>TL;DR:</strong> [Summary pending review]</p></div>'
                + result
            )

    return result


_FIDELITY_THINKING_TOKENS = 256


async def check_fidelity(
    blog_html: str,
    brand_voice_profile: dict | None,
    thinking_tokens: int = _FIDELITY_THINKING_TOKENS,
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

    # Build expanded scoring instructions for new BVP fields (advisory -- no pass/fail impact)
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

    response = await _client.aio.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=_thinking_config(thinking_tokens),
    )
    raw = _strip_fences(response.text.strip())

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("check_fidelity: Gemini returned invalid JSON: %r", raw[:200])
        raise ValueError(f"check_fidelity: Gemini returned invalid JSON: {exc}") from exc

    for key in ("tone_score", "cadence_score", "jargon_violations"):
        if key not in data:
            raise ValueError(f"check_fidelity: missing key '{key}' in Gemini response")
        if not isinstance(data[key], (int, float)):
            raise ValueError(
                f"check_fidelity: '{key}' must be numeric, got {type(data[key]).__name__}"
            )

    seo_bool_keys = ("seo_bluf_present", "seo_faq_present", "seo_fluff_detected")
    for key in seo_bool_keys:
        if key not in data:
            raise ValueError(f"check_fidelity: missing key '{key}' in Gemini response")
        if not isinstance(data[key], bool):
            raise ValueError(
                f"check_fidelity: '{key}' must be bool, got {type(data[key]).__name__}"
            )
    if "seo_h2_count" not in data:
        raise ValueError("check_fidelity: missing key 'seo_h2_count' in Gemini response")
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

    # Advisory fields: store if present, no validation failure if missing or wrong type.
    # These do NOT affect the pass/fail badge (tone >= 7, cadence >= 6, jargon_violations == 0 unchanged).
    for advisory_key in ("pronoun_score", "specificity_score"):
        if advisory_key in data and not isinstance(data[advisory_key], (int, float)):
            data[advisory_key] = None  # coerce invalid type silently
    if "closing_match" in data and not isinstance(data["closing_match"], bool):
        data["closing_match"] = None  # coerce invalid type silently

    return data


async def generate_social(
    brain_dump: str,
    blog_title: str,
    brand_voice_profile: dict | None,
    thinking_tokens: int = 0,
) -> dict:
    # Build bvp_json for the BRAND VOICE PROFILE section.
    # voice_brief is excluded from bvp_json (X post must not receive it per AC 9).
    # A separate linkedin_voice_section injects Part A (prose only) for LinkedIn.
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

    response = await _client.aio.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=_thinking_config(thinking_tokens),
    )
    raw = _strip_fences(response.text.strip())

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("generate_social: Gemini returned invalid JSON: %r", raw[:200])
        raise ValueError(f"generate_social: Gemini returned invalid JSON: {exc}") from exc

    for key in ("x_post", "linkedin_post"):
        if key not in data:
            raise ValueError(f"generate_social: missing key '{key}' in Gemini response")
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
