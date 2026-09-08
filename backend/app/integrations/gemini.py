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
    _ANGLE_DIRECTIVE_TEMPLATE,
    _DEFAULT_VOICE,
    _BLOG_ASSIST_PROMPT,
    _BLOG_PROMPT,
    _FIDELITY_PROMPT,
    _REPAIR_BLOG_VOICE_PROMPT,
    _SOCIAL_PROMPT,
    _SOCIAL_STANDALONE_ASSIST_PROMPT,
    _SOCIAL_STANDALONE_PROMPT,
    _WEEK_PLAN_PROMPT,
    _build_samples_block,
    _build_seo_section,
    _build_social_universal_rules,
    _build_social_voice_signals,
    _build_standalone_voice_injection,
    _build_template_structure,
    _build_template_voice_line,
    _build_voice_injection,
    build_quick_read_override,
    build_voice_for_surface,
    _meta_voice_note,
    _strip_fences,
    _md_to_html,
    _strip_blog_trailer,
)
from app.services.angles import ANGLE_LABELS, KNOWN_CODES, _LINKEDIN_ORDER, _X_ORDER
from app.services.platform_limits import HARD_LIMITS, over_limit, sentence_boundary_truncate

logger = logging.getLogger(__name__)

_client = genai.Client(api_key=settings.GEMINI_API_KEY)

_MODEL = settings.GEMINI_MODEL
logger.info("Gemini model: %s", _MODEL)


_PLATFORM_DISPLAY_NAMES: dict[str, str] = {
    "x": "X (Twitter)",
    "linkedin": "LinkedIn",
    "instagram": "Instagram",
    "facebook_page": "Facebook",
    "threads": "Threads",
}


async def _repair_post(platform: str, text: str, caller: str) -> str:
    """Issue one repair call to shorten an over-limit post.

    If the model's repaired text is still over limit, falls back to
    sentence_boundary_truncate. Exactly one repair attempt -- no loops.
    No ellipsis appended. No em-dashes or double-dashes in prompt (project rule).
    """
    limit = HARD_LIMITS[platform]
    display_name = _PLATFORM_DISPLAY_NAMES.get(platform, platform)
    repair_prompt = (
        f"Shorten this {display_name} post to under {limit} characters. "
        "Preserve the opening hook, the core point, and the writer's voice. "
        "Return only the post text, no commentary."
        f"\n\n{text}"
    )
    try:
        response = await _client.aio.models.generate_content(
            model=_MODEL,
            contents=repair_prompt,
        )
        repaired = response.text.strip()
        if over_limit(platform, repaired) == 0 and repaired:
            logger.info("%s: repair_applied platform=%s original_len=%d repaired_len=%d", caller, platform, len(text), len(repaired))
            return repaired
        logger.warning(
            "%s: repair still over limit for %s (%d chars), falling back to sentence boundary",
            caller, platform, len(repaired),
        )
    except Exception as exc:
        logger.warning("%s: repair call failed for %s: %s -- falling back to sentence boundary", caller, platform, exc)

    return sentence_boundary_truncate(text, limit, platform=platform)


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
Do NOT use em-dashes or double-dashes (--). Rewrite the sentence to flow naturally without any dash form instead.
Return ONLY the paragraph. No heading, no explanation."""


def _thinking_config(thinking_tokens: int) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=thinking_tokens)
    )


def _json_thinking_config(thinking_tokens: int) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=thinking_tokens),
        response_mime_type="application/json",
    )


def _sanitize_json_str(raw: str) -> str:
    """Strip markdown fences, extract outermost JSON object, normalize smart quotes."""
    if raw.startswith("```"):
        parts = raw.split("```")
        inner = parts[1]
        if inner.startswith("json"):
            inner = inner[4:]
        raw = inner.strip()

    # Extract the outermost JSON object in case of surrounding prose
    match = re.search(r"\{.+\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)

    # Replace Unicode smart/curly quotes that commonly break JSON parsing
    raw = (
        raw
        .replace("“", '"')   # left double quotation mark
        .replace("”", '"')   # right double quotation mark
        .replace("‘", "'")   # left single quotation mark
        .replace("’", "'")   # right single quotation mark
        .replace("—", ", ")  # em-dash → comma (never emit the banned double-hyphen)
        .replace("–", "-")   # en-dash → plain dash
    )

    return raw


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
        config=_json_thinking_config(thinking_tokens),
    )

    raw = response.text.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: sanitize smart quotes, strip fences, extract outermost object
        sanitized = _sanitize_json_str(raw)
        try:
            data = json.loads(sanitized)
            logger.warning("BVP JSON required sanitization (smart quotes / fences)")
        except json.JSONDecodeError as exc:
            logger.error("Gemini returned invalid JSON: %r", raw[:500])
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
    target_word_count: str | None = None,
    article_template: str | None = None,
    generation_mode: str | None = None,
    voice_samples: list[dict] | None = None,
) -> str:
    is_assist = (generation_mode or "generate") == "assist"

    if is_assist:
        prompt = _BLOG_ASSIST_PROMPT.format(brain_dump=brain_dump)
    else:
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
                voice_section = _build_voice_injection(brand_voice_profile) + _build_template_voice_line(article_template)
            else:
                voice_section = json.dumps(brand_voice_profile) + _build_template_voice_line(article_template)
        else:
            voice_section = _DEFAULT_VOICE
            tone_list = "professional, clear, authoritative"
            cadence_instruction = "avg sentence length 15 words"
            banned_jargon_list = "none specified"

        meta_voice_note = _meta_voice_note(brand_voice_profile or {})

        seo_target_section, audience_section = _build_seo_section(target_keyword, target_audience, secondary_keywords)

        template_structure_override = _build_template_structure(article_template, meta_voice_note)

        _WORD_COUNT_MAP = {
            "300-500": "300-500 words",
            "600-1000": "600-1,000 words",
            "1500-2500": "1,500-2,500 words",
        }
        word_count_range = _WORD_COUNT_MAP.get(target_word_count or "", "900-1,500 words")

        if target_word_count == "300-500":
            length_override_section = build_quick_read_override(article_template)
        else:
            length_override_section = ""

        # Assist mode: no samples injection by design (AC 5 of Story 26.3)
        samples_block = _build_samples_block(voice_samples, max_count=3, prefer_short=False)

        prompt = _BLOG_PROMPT.format(
            voice_section=voice_section,
            samples_block=samples_block,
            meta_voice_note=meta_voice_note,
            brain_dump=brain_dump,
            tone_list=tone_list,
            cadence_instruction=cadence_instruction,
            banned_jargon_list=banned_jargon_list,
            seo_target_section=seo_target_section,
            audience_section=audience_section,
            word_count_range=word_count_range,
            template_structure_override=template_structure_override,
            length_override_section=length_override_section,
        )

    response = await _client.aio.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=_thinking_config(thinking_tokens),
    )
    result = _strip_blog_trailer(_md_to_html(_strip_fences(response.text.strip())))
    # Belt-and-suspenders: replace any em-dashes the model emitted despite the ban
    result = result.replace("—", ", ")

    # Post-processing validation pass (assist mode does not require TL;DR or multiple H2s)
    if "<h1" not in result.lower():
        logger.warning("generate_blog: Gemini output missing H1 tag")
    if not is_assist:
        h2_count = result.lower().count("<h2")
        if h2_count < 2:
            logger.warning("generate_blog: Gemini output has fewer than 2 H2 tags (%d found)", h2_count)
        if (
            (article_template or "").lower() not in ("listicle", "thought-leadership")
            and target_word_count != "300-500"
            and '<div class="tldr">' not in result
        ):
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
    brain_dump: str = "",
    voice_samples: list[dict] | None = None,
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
            "authored_passages_preserved": True,
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

    samples_block = _build_samples_block(voice_samples, max_count=3, prefer_short=False)

    prompt = _FIDELITY_PROMPT.format(
        bvp_json=json.dumps(brand_voice_profile),
        samples_block=samples_block,
        blog_html=blog_html,
        brain_dump_sample=brain_dump[:1500],
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


async def repair_blog_voice(
    html: str,
    failing_dimensions: list[str],
    voice_section: str,
    voice_samples: list[dict] | None = None,
    thinking_tokens: int = 256,
) -> str:
    """Repair a blog post to fix failing voice fidelity dimensions.

    Makes exactly ONE LLM call. Returns the full repaired HTML.
    Failing dimensions are stated explicitly so the model knows what to fix.
    Em-dashes are sanitized from output (project rule).
    """
    failing_text = "\n".join(f"- {d}" for d in failing_dimensions) if failing_dimensions else "- general voice mismatch"
    samples_block = _build_samples_block(voice_samples, max_count=3) if voice_samples else ""
    safe_html = html.replace("{", "{{").replace("}", "}}")

    prompt = _REPAIR_BLOG_VOICE_PROMPT.format(
        failing_dimensions=failing_text,
        voice_section=voice_section,
        samples_block=samples_block,
        blog_html=safe_html,
    )

    response = await _client.aio.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=_thinking_config(thinking_tokens),
    )
    result = _strip_blog_trailer(_md_to_html(_strip_fences(response.text.strip())))
    result = result.replace("—", ", ")
    return result


async def generate_social(
    brain_dump: str,
    blog_title: str,
    brand_voice_profile: dict | None,
    thinking_tokens: int = 0,
    voice_samples: list[dict] | None = None,
) -> dict:
    # Build bvp_json for the BRAND VOICE PROFILE section.
    # voice_brief is excluded from bvp_json (X post must not receive it per AC 9).
    # A separate linkedin_voice_section injects Part A (prose only) for LinkedIn.
    if brand_voice_profile:
        bvp_without_voice = {k: v for k, v in brand_voice_profile.items() if k != "voice_brief"}
        bvp_json = json.dumps(bvp_without_voice)
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
    else:
        bvp_json = _DEFAULT_VOICE
        tone_list = "professional, clear, authoritative"
        cadence_instruction = "avg sentence length 15 words"

    voice_brief = (brand_voice_profile or {}).get("voice_brief") or ""
    if voice_brief and brand_voice_profile:
        linkedin_built = build_voice_for_surface(brand_voice_profile, "linkedin")
        instagram_built = build_voice_for_surface(brand_voice_profile, "instagram")
        facebook_built = build_voice_for_surface(brand_voice_profile, "facebook")
        threads_built = build_voice_for_surface(brand_voice_profile, "threads")
        linkedin_voice_section = f"\n{linkedin_built}\n" if linkedin_built else ""
        instagram_voice_section = f"\n{instagram_built}\n" if instagram_built else ""
        facebook_voice_section = f"\n{facebook_built}\n" if facebook_built else ""
        threads_voice_section = f"\n{threads_built}\n" if threads_built else ""
    else:
        linkedin_voice_section = ""
        instagram_voice_section = ""
        facebook_voice_section = ""
        threads_voice_section = ""

    bvp_structure_hints = _build_standalone_voice_injection(brand_voice_profile or {})
    social_universal_rules = _build_social_universal_rules(
        brand_voice_profile or {}, tone_list, cadence_instruction
    )
    social_voice_signals = _build_social_voice_signals(brand_voice_profile or {})
    samples_block = _build_samples_block(voice_samples, max_count=2, prefer_short=True)

    prompt = _SOCIAL_PROMPT.format(
        bvp_json=bvp_json,
        linkedin_voice_section=linkedin_voice_section,
        instagram_voice_section=instagram_voice_section,
        facebook_voice_section=facebook_voice_section,
        threads_voice_section=threads_voice_section,
        bvp_structure_hints=bvp_structure_hints,
        samples_block=samples_block,
        social_universal_rules=social_universal_rules,
        social_voice_signals=social_voice_signals,
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

    for key in ("x_post", "linkedin_post", "instagram_caption", "facebook_post", "threads_post"):
        if key not in data:
            raise ValueError(f"generate_social: missing key '{key}' in Gemini response")
        if not isinstance(data[key], str):
            raise ValueError(
                f"generate_social: '{key}' must be a string, got {type(data[key]).__name__}"
            )
        if not data[key]:
            raise ValueError(f"generate_social: '{key}' must be non-empty")

    for key in ("x_post", "linkedin_post", "instagram_caption", "facebook_post", "threads_post"):
        data[key] = data[key].replace("—", ", ")

    if over_limit("x", data["x_post"]) > 0:
        logger.warning(
            "generate_social: X post exceeded %d chars (%d), attempting repair",
            HARD_LIMITS["x"], len(data["x_post"]),
        )
        data["x_post"] = await _repair_post("x", data["x_post"], "generate_social")

    ln_len = len(data["linkedin_post"])
    if over_limit("linkedin", data["linkedin_post"]) > 0:
        logger.warning(
            "generate_social: LinkedIn post exceeded %d chars (%d), attempting repair",
            HARD_LIMITS["linkedin"], ln_len,
        )
        data["linkedin_post"] = await _repair_post("linkedin", data["linkedin_post"], "generate_social")
    elif ln_len < 300:
        logger.warning(
            "generate_social: LinkedIn post length %d is below expected 300 chars",
            ln_len,
        )

    ig_len = len(data["instagram_caption"])
    if ig_len < 150:
        logger.warning(
            "generate_social: instagram_caption length %d is below expected 150 chars",
            ig_len,
        )
    elif over_limit("instagram", data["instagram_caption"]) > 0:
        logger.warning(
            "generate_social: instagram_caption exceeded %d chars (%d), attempting repair",
            HARD_LIMITS["instagram"], ig_len,
        )
        data["instagram_caption"] = await _repair_post("instagram", data["instagram_caption"], "generate_social")

    fb_len = len(data["facebook_post"])
    if fb_len < 200:
        logger.warning(
            "generate_social: facebook_post length %d is below expected 200 chars",
            fb_len,
        )
    elif over_limit("facebook_page", data["facebook_post"]) > 0:
        logger.warning(
            "generate_social: facebook_post exceeded %d chars (%d), attempting repair",
            HARD_LIMITS["facebook_page"], fb_len,
        )
        data["facebook_post"] = await _repair_post("facebook_page", data["facebook_post"], "generate_social")

    if over_limit("threads", data["threads_post"]) > 0:
        logger.warning(
            "generate_social: threads_post exceeded %d chars (%d), attempting repair",
            HARD_LIMITS["threads"], len(data["threads_post"]),
        )
        data["threads_post"] = await _repair_post("threads", data["threads_post"], "generate_social")

    return data


async def generate_social_standalone(
    brain_dump: str,
    brand_voice_profile: dict | None,
    thinking_tokens: int = 0,
    angle: str | None = None,
    hook: str | None = None,
    generation_mode: str | None = None,
    voice_samples: list[dict] | None = None,
) -> dict:
    """Generate standalone social posts for Plan My Week (no blog exists).

    Uses _SOCIAL_STANDALONE_PROMPT with native-post structure for both
    LinkedIn (1200-2500 chars, hook/structure/CTA) and X (70-280 chars,
    Hook->Value->Proof->Nudge). BVP fields opening_pattern, closing_pattern,
    and post_structure_template are injected as structure hints.

    When angle/hook are provided (roadmap path), an ANGLE DIRECTIVE is injected
    into the prompt to commit the post to one specific angle. When None (social_only
    brain-dump campaigns), behavior is identical to the pre-20.8 implementation.

    When generation_mode='assist', uses _SOCIAL_STANDALONE_ASSIST_PROMPT to preserve
    the author's own wording and only adapt it to each platform's format.
    """
    is_assist = (generation_mode or "generate") == "assist"

    if is_assist:
        prompt = _SOCIAL_STANDALONE_ASSIST_PROMPT.format(brain_dump=brain_dump)
    else:
        if brand_voice_profile:
            bvp_without_voice = {k: v for k, v in brand_voice_profile.items() if k != "voice_brief"}
            bvp_json = json.dumps(bvp_without_voice)
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
        else:
            bvp_json = _DEFAULT_VOICE
            tone_list = "professional, clear, authoritative"
            cadence_instruction = "avg sentence length 15 words"

        voice_brief = (brand_voice_profile or {}).get("voice_brief") or ""
        if voice_brief and brand_voice_profile:
            linkedin_built = build_voice_for_surface(brand_voice_profile, "linkedin")
            instagram_built = build_voice_for_surface(brand_voice_profile, "instagram")
            facebook_built = build_voice_for_surface(brand_voice_profile, "facebook")
            threads_built = build_voice_for_surface(brand_voice_profile, "threads")
            linkedin_voice_section = f"\n{linkedin_built}\n" if linkedin_built else ""
            instagram_voice_section = f"\n{instagram_built}\n" if instagram_built else ""
            facebook_voice_section = f"\n{facebook_built}\n" if facebook_built else ""
            threads_voice_section = f"\n{threads_built}\n" if threads_built else ""
        else:
            linkedin_voice_section = ""
            instagram_voice_section = ""
            facebook_voice_section = ""
            threads_voice_section = ""

        bvp_structure_hints = _build_standalone_voice_injection(brand_voice_profile or {})
        social_universal_rules = _build_social_universal_rules(
            brand_voice_profile or {}, tone_list, cadence_instruction
        )
        social_voice_signals = _build_social_voice_signals(brand_voice_profile or {})
        samples_block = _build_samples_block(voice_samples, max_count=2, prefer_short=True)

        prompt = _SOCIAL_STANDALONE_PROMPT.format(
            bvp_json=bvp_json,
            linkedin_voice_section=linkedin_voice_section,
            instagram_voice_section=instagram_voice_section,
            facebook_voice_section=facebook_voice_section,
            threads_voice_section=threads_voice_section,
            bvp_structure_hints=bvp_structure_hints,
            samples_block=samples_block,
            social_universal_rules=social_universal_rules,
            social_voice_signals=social_voice_signals,
            brain_dump=brain_dump,
        )

    if angle:
        display_label = ANGLE_LABELS.get(angle, angle)
        hook_line = f"- Opening thesis / hook to build from: {hook}\n" if hook else ""
        prompt = prompt + _ANGLE_DIRECTIVE_TEMPLATE.format(
            display_label=display_label,
            hook_line=hook_line,
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
        logger.error("generate_social_standalone: Gemini returned invalid JSON: %r", raw[:200])
        raise ValueError(f"generate_social_standalone: Gemini returned invalid JSON: {exc}") from exc

    for key in ("x_post", "linkedin_post", "instagram_caption", "facebook_post", "threads_post"):
        if key not in data:
            raise ValueError(f"generate_social_standalone: missing key '{key}' in Gemini response")
        if not isinstance(data[key], str):
            raise ValueError(
                f"generate_social_standalone: '{key}' must be a string, got {type(data[key]).__name__}"
            )
        if not data[key]:
            raise ValueError(f"generate_social_standalone: '{key}' must be non-empty")

    for key in ("x_post", "linkedin_post", "instagram_caption", "facebook_post", "threads_post"):
        data[key] = data[key].replace("—", ", ")

    if over_limit("x", data["x_post"]) > 0:
        logger.warning(
            "generate_social_standalone: X post exceeded %d chars (%d), attempting repair",
            HARD_LIMITS["x"], len(data["x_post"]),
        )
        data["x_post"] = await _repair_post("x", data["x_post"], "generate_social_standalone")

    ln_len = len(data["linkedin_post"])
    if over_limit("linkedin", data["linkedin_post"]) > 0:
        logger.warning(
            "generate_social_standalone: LinkedIn post exceeded %d chars (%d), attempting repair",
            HARD_LIMITS["linkedin"], ln_len,
        )
        data["linkedin_post"] = await _repair_post("linkedin", data["linkedin_post"], "generate_social_standalone")
    elif ln_len < 1200:
        logger.warning(
            "generate_social_standalone: LinkedIn post length %d is below expected 1200 chars",
            ln_len,
        )

    ig_len = len(data["instagram_caption"])
    if ig_len < 150:
        logger.warning(
            "generate_social_standalone: instagram_caption length %d is below expected 150 chars",
            ig_len,
        )
    elif over_limit("instagram", data["instagram_caption"]) > 0:
        logger.warning(
            "generate_social_standalone: instagram_caption exceeded %d chars (%d), attempting repair",
            HARD_LIMITS["instagram"], ig_len,
        )
        data["instagram_caption"] = await _repair_post("instagram", data["instagram_caption"], "generate_social_standalone")

    fb_len = len(data["facebook_post"])
    if fb_len < 200:
        logger.warning(
            "generate_social_standalone: facebook_post length %d is below expected 200 chars",
            fb_len,
        )
    elif over_limit("facebook_page", data["facebook_post"]) > 0:
        logger.warning(
            "generate_social_standalone: facebook_post exceeded %d chars (%d), attempting repair",
            HARD_LIMITS["facebook_page"], fb_len,
        )
        data["facebook_post"] = await _repair_post("facebook_page", data["facebook_post"], "generate_social_standalone")

    if over_limit("threads", data["threads_post"]) > 0:
        logger.warning(
            "generate_social_standalone: threads_post exceeded %d chars (%d), attempting repair",
            HARD_LIMITS["threads"], len(data["threads_post"]),
        )
        data["threads_post"] = await _repair_post("threads", data["threads_post"], "generate_social_standalone")

    return data


async def generate_week_plan(
    brain_dump: str,
    brand_voice_profile: dict | None,
    linkedin_count: int,
    twitter_count: int,
) -> dict:
    """Plan a diverse week of social posts -- one LLM call that sees all slots at once.

    Returns:
        {
          "linkedin": [{"angle": str, "hook": str, "facet": str}, ...],  # linkedin_count entries
          "x":        [{"angle": str, "hook": str, "facet": str}, ...],  # twitter_count entries
        }

    Each entry uses a distinct angle code from the taxonomy. Shape is validated and
    minimally repaired (unknown codes are replaced with fallback codes). Raises
    ValueError if the response cannot be parsed at all (caller must fall back).
    """
    bvp_json = json.dumps(
        {k: v for k, v in brand_voice_profile.items() if k != "voice_brief"}
        if brand_voice_profile else {}
    )
    linkedin_angles = ", ".join(_LINKEDIN_ORDER)
    x_angles = ", ".join(_X_ORDER)

    prompt = _WEEK_PLAN_PROMPT.format(
        bvp_json=bvp_json,
        brain_dump=brain_dump,
        linkedin_count=linkedin_count,
        twitter_count=twitter_count,
        linkedin_angles=linkedin_angles,
        x_angles=x_angles,
    )

    response = await _client.aio.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=_thinking_config(0),
    )
    raw = _strip_fences(response.text.strip())

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("generate_week_plan: Gemini returned invalid JSON: %r", raw[:200])
        raise ValueError(f"generate_week_plan: Gemini returned invalid JSON: {exc}") from exc

    if not isinstance(data.get("linkedin"), list) or not isinstance(data.get("x"), list):
        raise ValueError("generate_week_plan: missing 'linkedin' or 'x' list in response")

    data["linkedin"] = _repair_plan_entries(data["linkedin"], linkedin_count, "linkedin")
    data["x"] = _repair_plan_entries(data["x"], twitter_count, "x")

    return data


def _repair_plan_entries(entries: list, expected: int, platform: str) -> list:
    """Validate and minimally repair plan entries for one platform.

    - Entries with unknown or duplicate angle codes are replaced with the next fallback.
    - If fewer entries than expected, pads with unused pool codes before cycling.
    - Truncates if more entries than expected (shouldn't happen but defensive).
    """
    valid: list[dict] = []
    used_angles: list[str] = []

    for entry in entries[:expected]:
        if not isinstance(entry, dict):
            continue
        code = entry.get("angle", "")
        if code not in KNOWN_CODES or code in used_angles:
            code = _next_fallback(platform, used_angles)
        hook = str(entry.get("hook") or "").strip().replace("—", ", ")
        facet = str(entry.get("facet") or "").strip()
        valid.append({"angle": code, "hook": hook, "facet": facet})
        used_angles.append(code)

    missing = expected - len(valid)
    if missing > 0:
        pad_angles = _pad_fallback(platform, used_angles, missing)
        for code in pad_angles:
            valid.append({"angle": code, "hook": "", "facet": ""})

    return valid


def _next_fallback(platform: str, used: list[str]) -> str:
    pool = _LINKEDIN_ORDER if platform == "linkedin" else _X_ORDER
    for code in pool:
        if code not in used:
            return code
    return pool[len(used) % len(pool)]


def _pad_fallback(platform: str, used: list[str], count: int) -> list[str]:
    pool = _LINKEDIN_ORDER if platform == "linkedin" else _X_ORDER
    result: list[str] = []
    # Prefer codes not yet used before cycling
    for code in pool:
        if code not in used and len(result) < count:
            result.append(code)
    # Cycle from pool start for any remaining slots
    idx = 0
    while len(result) < count:
        result.append(pool[idx % len(pool)])
        idx += 1
    return result
