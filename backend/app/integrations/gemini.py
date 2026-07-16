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

logger = logging.getLogger(__name__)

_client = genai.Client(api_key=settings.GEMINI_API_KEY)

_MODEL = settings.GEMINI_MODEL
logger.info("Gemini model: %s", _MODEL)

_BVP_PROMPT_TEMPLATE = """Analyze the following text and extract a Brand Voice Profile.

Return ONLY a valid JSON object with this exact schema:
{{
  "tone": ["list", "of", "style", "descriptors"],
  "cadence": {{
    "avg_sentence_length": <integer>,
    "variation_pattern": "<string>",
    "paragraph_structure": "<string>"
  }},
  "banned_jargon": ["words", "or", "phrases", "to", "avoid"],
  "target_audience": "<one sentence describing who this brand writes for, inferred from the content, or null if unclear>"
}}

No markdown code blocks, no explanation. Raw JSON only.

TEXT TO ANALYZE:
{text}"""


def _thinking_config(thinking_tokens: int) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=thinking_tokens)
    )


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

    return data


_DEFAULT_VOICE = (
    "professional, clear, and authoritative tone; moderate cadence; avoid jargon"
)

_BLOG_PROMPT = """You are a direct, expert blog writer. Write a blog post that sounds like a human expert, not an AI assistant.

BRAND VOICE PROFILE:
{bvp_json}

BRAIN DUMP (author's raw ideas — build the blog around the core argument, but RETAIN all first-person experiences, specific numbers, dates, named tools, or unique outcomes. These are E-E-A-T and Information Gain signals; do not generalize or anonymize them):
{brain_dump}

{seo_target_section}
{audience_section}

MANDATORY STRUCTURE (HTML only, no markdown — follow this EXACTLY):
<h1>[Keyword-first title, specific and direct]</h1>
<!-- meta: [One sentence meta description, max 150 chars, ends with action phrase] -->
<div class="tldr"><p><strong>TL;DR:</strong> [2-3 bold sentences that directly answer the post's core question. Specific. No filler.]</p></div>
<p>[BLUF intro paragraph: Start with a specific fact, number, or bold claim. Never start with "In today's..." or similar openers. State the core takeaway in the first sentence.]</p>
<h2>[Main topic — actionable heading]</h2>
[GEO RULE: If this H2 implies a direct question (How to, Why, What is, When should you): open with a direct 1–3 sentence answer paragraph (max ~60 words) BEFORE the H3 — this is the AI Overview citation extract. If the H2 is built around examples, comparisons, step-by-step processes, or data: skip the answer block and lead straight into the H3. Never force an answer block where it does not arise naturally.]
<h3>[Sub-topic]</h3>
<p>...</p>
[Repeat this H2 pattern for each main content section (3 to 4 total, not counting the FAQ and Key Takeaways sections below)]
<h2>Frequently Asked Questions</h2>
<dl class="faq">
  <dt>[Question 1 related to the post topic]</dt>
  <dd><strong>[Direct one-sentence answer.]</strong> [1-2 sentence explanation.]</dd>
  <dt>[Question 2]</dt>
  <dd><strong>[Direct one-sentence answer.]</strong> [1-2 sentence explanation.]</dd>
  <dt>[Question 3]</dt>
  <dd><strong>[Direct one-sentence answer.]</strong> [1-2 sentence explanation.]</dd>
</dl>
<h2>Key Takeaways</h2>
<p>[Conclusion paragraph that leads with the single most important action the reader should take. Do not restate the intro.]</p>

REQUIREMENTS:
- Target 900-1,500 words
- Use H2 and H3 for structure; only one H1 (the title)
- Match the tone: {tone_list}
- Match the cadence: avg sentence length {avg_sentence_length} words
- Never use these jargon terms: {banned_jargon_list}
- If the Brain Dump says "I found X", "I tested X", or "I built X" — use first-person voice in the post. Never convert "I found conversion increased 40%" into "conversion rates can increase up to 40%". The author's direct experience is the E-E-A-T signal.
- If the Brain Dump contains proprietary data, A/B test results, client outcomes, or specific findings not commonly known — surface these in the opening of the relevant H2 section. Do not bury unique data behind generic context-setting paragraphs.
- Output ONLY valid HTML tags — NEVER use markdown syntax like **bold**, *italic*, ##, ###
- Bold text must use <strong>, italics must use <em>

BANNED OPENERS — never start any paragraph or sentence with these phrases:
- "In today's fast-paced world"
- "In today's digital landscape"
- "As we all know"
- "It's no secret that"
- "The [anything] landscape is evolving"
- "Standing out requires more than"
- "Now more than ever"

BANNED WORDS — do not use anywhere: delve, moreover, testament, comprehensive, furthermore, tapestry, paradigm, bespoke, unlock, supercharge, navigate (as metaphor)

Every sentence must earn its place. If a sentence does not give the reader new information or a specific action, cut it.
"""

_FIDELITY_PROMPT = """Evaluate the following blog post against the Brand Voice Profile AND for SEO quality.

BRAND VOICE PROFILE:
{bvp_json}

BLOG HTML:
{blog_html}

Return ONLY a valid JSON object (no markdown):
{{
  "tone_score": <integer 0-10>,
  "cadence_score": <integer 0-10>,
  "jargon_violations": <integer count of banned BVP terms found>,
  "seo_bluf_present": <boolean: true if the first <p> tag starts with a specific fact, stat, or direct claim — NOT a general statement like "The landscape is..."; false otherwise>,
  "seo_h2_count": <integer: count of <h2> tags in the blog HTML>,
  "seo_faq_present": <boolean: true if a FAQ section with at least 3 Q&A pairs (as <dl> or similar) is present>,
  "seo_fluff_detected": <boolean: true if any banned opener phrase like "In today's fast-paced world", "As we all know", "It's no secret that" appears anywhere in the content>,
  "tags": [<list of 3-5 concise lowercase SEO tags relevant to this specific post, e.g. ["brand voice", "content marketing", "ai tools"]>]
}}
"""

_SOCIAL_PROMPT = """Based on the brain dump and brand voice, write two social media posts.

BRAND VOICE PROFILE:
{bvp_json}

BRAIN DUMP:
{brain_dump}

BLOG TITLE:
{blog_title}

Return ONLY a valid JSON object (no markdown):
{{
  "x_post": "<X post text, max 280 characters, tease the blog without duplicating it>",
  "linkedin_post": "<LinkedIn post, 500-1300 characters, use blank lines for paragraph breaks. Must open with a first-person hook tied to the brain dump's key insight — acceptable openers: 'I just discovered...', 'Last week I...', 'After testing X, I found...'. Tease the specific outcome from the brain dump, not the general topic.>"
}}
"""


def _build_seo_section(
    target_keyword: str | None,
    target_audience: str | None,
    secondary_keywords: str | None = None,
) -> tuple[str, str]:
    if target_keyword:
        seo_section = f"""SEO TARGET:
- Primary keyword: {target_keyword}
- Include this exact phrase or a close variant in: the H1 title, the first 100 words, at least one H2 heading, and the conclusion paragraph.
- Write to rank for this specific search query — assume the reader typed this exact phrase into Google."""
    else:
        seo_section = """SEARCH INTENT FOCUS (no keyword provided):
Extract the single most specific, actionable angle from the Brain Dump. Pick ONE target reader type — not "developers AND marketers", not "apps AND SaaS". Choose one. Write exclusively for that angle. State your choice in the H1 and commit to it through every section. If the brain dump is broad, pick the most specific, technical angle."""

    if secondary_keywords:
        seo_section += f"""

SUPPORTING KEYWORDS (mention each at most once, naturally):
{secondary_keywords}
- Place each term at most once within the first 500 words, only inside a sentence that already calls for it.
- If no natural sentence exists for a term, skip it entirely — forced insertion is worse than omission."""

    audience_section = ""
    if target_audience:
        audience_section = f"""TARGET AUDIENCE:
- {target_audience}
- Write exclusively for this audience. Do not broaden the scope. If a reference or tool would be unfamiliar to this audience, explain it in one clause or omit it."""

    return seo_section, audience_section


def _strip_fences(raw: str) -> str:
    fence_start = raw.find("```")
    if fence_start == -1:
        return raw
    lines = raw[fence_start:].split("\n")
    start = 1
    end = len(lines)
    if lines and lines[-1].strip() == "```":
        end -= 1
    return "\n".join(lines[start:end]).strip()


def _md_to_html(html: str) -> str:
    """Fix markdown syntax that Gemini leaks inside otherwise-valid HTML."""
    # **bold** → <strong>bold</strong>
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html, flags=re.DOTALL)
    # *italic* → <em>italic</em> (single asterisks not part of **)
    html = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", html, flags=re.DOTALL)
    # ## Heading / ### Heading at the start of a line (if Gemini emits bare markdown headings)
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
    return html


async def generate_blog(
    brain_dump: str,
    brand_voice_profile: dict | None,
    thinking_tokens: int = 512,
    target_keyword: str | None = None,
    target_audience: str | None = None,
    secondary_keywords: str | None = None,
) -> str:
    if brand_voice_profile:
        bvp_json = json.dumps(brand_voice_profile)
        tone_list = ", ".join(str(t) for t in brand_voice_profile.get("tone", []))
        cadence = brand_voice_profile.get("cadence", {})
        avg_sentence_length = cadence.get("avg_sentence_length", 15)
        banned_jargon_list = ", ".join(str(j) for j in brand_voice_profile.get("banned_jargon", []))
    else:
        bvp_json = _DEFAULT_VOICE
        tone_list = "professional, clear, authoritative"
        avg_sentence_length = 15
        banned_jargon_list = "none specified"

    seo_target_section, audience_section = _build_seo_section(target_keyword, target_audience, secondary_keywords)

    prompt = _BLOG_PROMPT.format(
        bvp_json=bvp_json,
        brain_dump=brain_dump,
        tone_list=tone_list,
        avg_sentence_length=avg_sentence_length,
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

    prompt = _FIDELITY_PROMPT.format(
        bvp_json=json.dumps(brand_voice_profile),
        blog_html=blog_html,
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

    return data


async def generate_social(
    brain_dump: str,
    blog_title: str,
    brand_voice_profile: dict | None,
    thinking_tokens: int = 0,
) -> dict:
    bvp_json = json.dumps(brand_voice_profile) if brand_voice_profile else _DEFAULT_VOICE

    prompt = _SOCIAL_PROMPT.format(
        bvp_json=bvp_json,
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
