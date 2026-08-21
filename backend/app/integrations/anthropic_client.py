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
    _ANGLE_DIRECTIVE_TEMPLATE,
    _DEFAULT_VOICE,
    _BLOG_ASSIST_PROMPT,
    _BLOG_PROMPT,
    _FIDELITY_PROMPT,
    _SOCIAL_PROMPT,
    _SOCIAL_STANDALONE_PROMPT,
    _WEEK_PLAN_PROMPT,
    _build_seo_section,
    _build_social_universal_rules,
    _build_standalone_voice_injection,
    _build_template_structure,
    _build_voice_injection,
    _meta_voice_note,
    _strip_fences,
    _md_to_html,
    _strip_blog_trailer,
)
from app.services.angles import ANGLE_LABELS, KNOWN_CODES, fallback_angles, _LINKEDIN_ORDER, _X_ORDER

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
    target_word_count: str | None = None,
    article_template: str | None = None,
    generation_mode: str | None = None,
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

        template_structure_override = _build_template_structure(article_template, meta_voice_note)

        _WORD_COUNT_MAP = {
            "300-500": "300-500 words",
            "600-1000": "600-1,000 words",
            "1500-2500": "1,500-2,500 words",
        }
        word_count_range = _WORD_COUNT_MAP.get(target_word_count or "", "900-1,500 words")

        if target_word_count == "300-500":
            length_override_section = (
                "QUICK READ MODE (300-500 words):\n"
                "- Strict word limit: 300-500 words total including all headings and HTML.\n"
                "- OMIT the <div class=\"tldr\"> block entirely. Do not output it.\n"
                "- OMIT the <h2>Frequently Asked Questions</h2> and <dl class=\"faq\"> block entirely.\n"
                "- Write 1-2 H2 body sections only (not 3-4).\n"
                "- The BLUF intro paragraph and conclusion are still required.\n"
                "- Every sentence must earn its place. Cut anything that does not give the reader\n"
                "  a new fact or a specific action."
            )
        else:
            length_override_section = ""

        prompt = _BLOG_PROMPT.format(
            voice_section=voice_section,
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

    max_tokens = max(8192, thinking_tokens + 4096)
    if thinking_tokens > 0:
        raw = await _call_with_thinking(prompt, max_tokens, thinking_tokens)
    else:
        raw = await _call(prompt, max_tokens)

    result = _strip_blog_trailer(_md_to_html(_strip_fences(raw.strip())))
    result = result.replace("—", ", ")

    # Post-processing validation pass (assist mode does not require TL;DR or multiple H2s)
    if "<h1" not in result.lower():
        logger.warning("generate_blog: Anthropic output missing H1 tag")
    if not is_assist:
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
    brain_dump: str = "",
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
        brain_dump_sample=brain_dump[:1500],
        expanded_scoring_section=expanded_scoring_section,
    )

    raw = _strip_fences((await _call(prompt, max_tokens=2048)).strip())

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
    if voice_brief:
        linkedin_voice_section = (
            "\nLINKEDIN BRAND VOICE (apply to linkedin_post only -- do not apply to x_post):\n"
            f"{voice_brief}\n"
        )
        instagram_voice_section = (
            "\nINSTAGRAM BRAND VOICE (apply to instagram_caption only):\n"
            f"{voice_brief}\n"
        )
        facebook_voice_section = (
            "\nFACEBOOK BRAND VOICE (apply to facebook_post only):\n"
            f"{voice_brief}\n"
        )
        sentences = [s.strip() for s in voice_brief.split(". ") if s.strip()]
        brief_excerpt = ". ".join(sentences[:2])
        if brief_excerpt and not brief_excerpt.endswith("."):
            brief_excerpt += "."
        threads_voice_section = (
            "\nTHREADS BRAND VOICE (apply to threads_post only -- keep it raw and unpolished; "
            "voice is for register, not formality):\n"
            f"{brief_excerpt}\n"
        )
    else:
        linkedin_voice_section = ""
        instagram_voice_section = ""
        facebook_voice_section = ""
        threads_voice_section = ""

    bvp_structure_hints = _build_standalone_voice_injection(brand_voice_profile or {})
    social_universal_rules = _build_social_universal_rules(
        brand_voice_profile or {}, tone_list, cadence_instruction
    )

    prompt = _SOCIAL_PROMPT.format(
        bvp_json=bvp_json,
        linkedin_voice_section=linkedin_voice_section,
        instagram_voice_section=instagram_voice_section,
        facebook_voice_section=facebook_voice_section,
        threads_voice_section=threads_voice_section,
        bvp_structure_hints=bvp_structure_hints,
        social_universal_rules=social_universal_rules,
        brain_dump=brain_dump,
        blog_title=blog_title,
    )

    raw = _strip_fences((await _call(prompt, max_tokens=4096)).strip())

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("generate_social: Anthropic returned invalid JSON: %r", raw[:200])
        raise ValueError(f"generate_social: Anthropic returned invalid JSON: {exc}") from exc

    for key in ("x_post", "linkedin_post", "instagram_caption", "facebook_post", "threads_post"):
        if key not in data:
            raise ValueError(f"generate_social: missing key '{key}' in Anthropic response")
        if not isinstance(data[key], str):
            raise ValueError(
                f"generate_social: '{key}' must be a string, got {type(data[key]).__name__}"
            )
        if not data[key]:
            raise ValueError(f"generate_social: '{key}' must be non-empty")

    for key in ("x_post", "linkedin_post", "instagram_caption", "facebook_post", "threads_post"):
        data[key] = data[key].replace("—", ", ")

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
    elif ig_len > 600:
        logger.warning(
            "generate_social: instagram_caption exceeded 600 chars (%d), truncating", ig_len,
        )
        data["instagram_caption"] = data["instagram_caption"][:599] + "…"

    fb_len = len(data["facebook_post"])
    if fb_len < 200:
        logger.warning(
            "generate_social: facebook_post length %d is below expected 200 chars",
            fb_len,
        )
    elif fb_len > 800:
        logger.warning(
            "generate_social: facebook_post exceeded 800 chars (%d), truncating", fb_len,
        )
        data["facebook_post"] = data["facebook_post"][:799] + "…"

    if len(data["threads_post"]) > 500:
        logger.warning(
            "generate_social: threads_post exceeded 500 chars (%d), truncating",
            len(data["threads_post"]),
        )
        data["threads_post"] = data["threads_post"][:499] + "…"

    return data


async def generate_social_standalone(
    brain_dump: str,
    brand_voice_profile: dict | None,
    thinking_tokens: int = 0,
    angle: str | None = None,
    hook: str | None = None,
) -> dict:
    """Generate standalone social posts for Plan My Week (no blog exists).

    Uses _SOCIAL_STANDALONE_PROMPT with native-post structure for both
    LinkedIn (1200-2500 chars, hook/structure/CTA) and X (70-280 chars,
    Hook->Value->Proof->Nudge). BVP fields opening_pattern, closing_pattern,
    and post_structure_template are injected as structure hints.

    When angle/hook are provided (roadmap path), an ANGLE DIRECTIVE is injected
    into the prompt to commit the post to one specific angle. When None (social_only
    brain-dump campaigns), behavior is identical to the pre-20.8 implementation.
    """
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
    if voice_brief:
        linkedin_voice_section = (
            "\nLINKEDIN BRAND VOICE (apply to linkedin_post only -- do not apply to x_post):\n"
            f"{voice_brief}\n"
        )
        instagram_voice_section = (
            "\nINSTAGRAM BRAND VOICE (apply to instagram_caption only):\n"
            f"{voice_brief}\n"
        )
        facebook_voice_section = (
            "\nFACEBOOK BRAND VOICE (apply to facebook_post only):\n"
            f"{voice_brief}\n"
        )
        sentences = [s.strip() for s in voice_brief.split(". ") if s.strip()]
        brief_excerpt = ". ".join(sentences[:2])
        if brief_excerpt and not brief_excerpt.endswith("."):
            brief_excerpt += "."
        threads_voice_section = (
            "\nTHREADS BRAND VOICE (apply to threads_post only -- keep it raw and unpolished; "
            "voice is for register, not formality):\n"
            f"{brief_excerpt}\n"
        )
    else:
        linkedin_voice_section = ""
        instagram_voice_section = ""
        facebook_voice_section = ""
        threads_voice_section = ""

    bvp_structure_hints = _build_standalone_voice_injection(brand_voice_profile or {})
    social_universal_rules = _build_social_universal_rules(
        brand_voice_profile or {}, tone_list, cadence_instruction
    )

    prompt = _SOCIAL_STANDALONE_PROMPT.format(
        bvp_json=bvp_json,
        linkedin_voice_section=linkedin_voice_section,
        instagram_voice_section=instagram_voice_section,
        facebook_voice_section=facebook_voice_section,
        threads_voice_section=threads_voice_section,
        bvp_structure_hints=bvp_structure_hints,
        social_universal_rules=social_universal_rules,
        brain_dump=brain_dump,
    )

    if angle:
        display_label = ANGLE_LABELS.get(angle, angle)
        hook_line = f"- Opening thesis / hook to build from: {hook}\n" if hook else ""
        prompt = prompt + _ANGLE_DIRECTIVE_TEMPLATE.format(
            display_label=display_label,
            hook_line=hook_line,
        )

    raw = _strip_fences((await _call(prompt, max_tokens=6144)).strip())

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("generate_social_standalone: Anthropic returned invalid JSON: %r", raw[:200])
        raise ValueError(f"generate_social_standalone: Anthropic returned invalid JSON: {exc}") from exc

    for key in ("x_post", "linkedin_post", "instagram_caption", "facebook_post", "threads_post"):
        if key not in data:
            raise ValueError(f"generate_social_standalone: missing key '{key}' in Anthropic response")
        if not isinstance(data[key], str):
            raise ValueError(
                f"generate_social_standalone: '{key}' must be a string, got {type(data[key]).__name__}"
            )
        if not data[key]:
            raise ValueError(f"generate_social_standalone: '{key}' must be non-empty")

    for key in ("x_post", "linkedin_post", "instagram_caption", "facebook_post", "threads_post"):
        data[key] = data[key].replace("—", ", ")

    if len(data["x_post"]) > 280:
        logger.warning(
            "generate_social_standalone: X post exceeded 280 chars (%d), truncating",
            len(data["x_post"]),
        )
        data["x_post"] = data["x_post"][:279] + "…"

    ln_len = len(data["linkedin_post"])
    if ln_len > 2500:
        logger.warning(
            "generate_social_standalone: LinkedIn post exceeded 2500 chars (%d), truncating",
            ln_len,
        )
        data["linkedin_post"] = data["linkedin_post"][:2499] + "…"
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
    elif ig_len > 600:
        logger.warning(
            "generate_social_standalone: instagram_caption exceeded 600 chars (%d), truncating", ig_len,
        )
        data["instagram_caption"] = data["instagram_caption"][:599] + "…"

    fb_len = len(data["facebook_post"])
    if fb_len < 200:
        logger.warning(
            "generate_social_standalone: facebook_post length %d is below expected 200 chars",
            fb_len,
        )
    elif fb_len > 800:
        logger.warning(
            "generate_social_standalone: facebook_post exceeded 800 chars (%d), truncating", fb_len,
        )
        data["facebook_post"] = data["facebook_post"][:799] + "…"

    if len(data["threads_post"]) > 500:
        logger.warning(
            "generate_social_standalone: threads_post exceeded 500 chars (%d), truncating",
            len(data["threads_post"]),
        )
        data["threads_post"] = data["threads_post"][:499] + "…"

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

    raw = _strip_fences((await _call(prompt, max_tokens=2048)).strip())

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("generate_week_plan: Anthropic returned invalid JSON: %r", raw[:200])
        raise ValueError(f"generate_week_plan: Anthropic returned invalid JSON: {exc}") from exc

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

    # Pad missing entries
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
