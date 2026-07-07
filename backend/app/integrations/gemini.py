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

_MODEL = "gemini-2.5-flash"

_BVP_PROMPT_TEMPLATE = """Analyze the following text and extract a Brand Voice Profile.

Return ONLY a valid JSON object with this exact schema:
{{
  "tone": ["list", "of", "style", "descriptors"],
  "cadence": {{
    "avg_sentence_length": <integer>,
    "variation_pattern": "<string>",
    "paragraph_structure": "<string>"
  }},
  "banned_jargon": ["words", "or", "phrases", "to", "avoid"]
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

    return data


_DEFAULT_VOICE = (
    "professional, clear, and authoritative tone; moderate cadence; avoid jargon"
)

_BLOG_PROMPT = """You are an expert blog writer. Using the Brand Voice Profile provided, \
write an SEO-optimized blog post in semantic HTML format.

BRAND VOICE PROFILE:
{bvp_json}

BRAIN DUMP (author's raw idea):
{brain_dump}

OUTPUT FORMAT (HTML only, no markdown fences):
<h1>Title Here</h1>
<!-- meta: One sentence meta description for SEO -->
<h2>Section Heading</h2>
<p>Body paragraph...</p>
...
<h2>Conclusion</h2>
<p>Closing paragraph...</p>

REQUIREMENTS:
- Target 800-1,500 words
- Use H2 and H3 for structure; only one H1 (the title)
- Match the tone: {tone_list}
- Match the cadence: avg sentence length {avg_sentence_length} words
- Never use these jargon terms: {banned_jargon_list}
- Output ONLY valid HTML tags — NEVER use markdown syntax like **bold**, *italic*, ##, ###
- Bold text must use <strong>, italics must use <em>, headings must use <h2>/<h3> tags
"""

_FIDELITY_PROMPT = """Score the following blog post against the Brand Voice Profile.

BRAND VOICE PROFILE:
{bvp_json}

BLOG HTML:
{blog_html}

Return ONLY a valid JSON object (no markdown):
{{
  "tone_score": <integer 0-10>,
  "cadence_score": <integer 0-10>,
  "jargon_violations": <integer count of banned terms found>
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
  "linkedin_post": "<LinkedIn post, 500-1300 characters, use blank lines for paragraph breaks>"
}}
"""


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

    prompt = _BLOG_PROMPT.format(
        bvp_json=bvp_json,
        brain_dump=brain_dump,
        tone_list=tone_list,
        avg_sentence_length=avg_sentence_length,
        banned_jargon_list=banned_jargon_list,
    )

    response = await _client.aio.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=_thinking_config(thinking_tokens),
    )
    return _md_to_html(_strip_fences(response.text.strip()))


async def check_fidelity(
    blog_html: str,
    brand_voice_profile: dict | None,
    thinking_tokens: int = 256,
) -> dict:
    if brand_voice_profile is None:
        return {"tone_score": 10, "cadence_score": 10, "jargon_violations": 0}

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
