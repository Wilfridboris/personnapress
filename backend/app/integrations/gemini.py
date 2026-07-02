"""Gemini LLM integration.

Called ONLY from services/ingestion.py and services/generation.py (AR-19).
Do not call this module directly from routers or workers.
"""

import json
import logging

import google.generativeai as genai

from app.core.config import settings

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.GEMINI_API_KEY)

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


async def extract_brand_voice(text: str, thinking_tokens: int = 1024) -> dict:
    """Call Gemini 2.5 Flash to extract a Brand Voice Profile from text.

    Args:
        text: The combined text content to analyze (capped at 50 000 chars by caller).
        thinking_tokens: Gemini thinking token budget (default 1024 per NFR-9).

    Returns:
        A dict with keys: tone (list[str]), cadence (dict), banned_jargon (list[str]).

    Raises:
        ValueError: If Gemini returns a response that cannot be parsed as the expected JSON.
    """
    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        generation_config={"thinking_budget": thinking_tokens},
    )

    prompt = _BVP_PROMPT_TEMPLATE.format(text=text[:50_000])

    response = await model.generate_content_async(prompt)

    raw = response.text.strip()

    # Strip optional markdown code fences the model may still add
    if raw.startswith("```"):
        parts = raw.split("```")
        # parts[1] is the content inside the fences
        inner = parts[1]
        if inner.startswith("json"):
            inner = inner[4:]
        raw = inner.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Gemini returned invalid JSON: %r", raw[:200])
        raise ValueError(f"Gemini returned invalid JSON: {exc}") from exc

    # Structural validation
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
- Output ONLY the HTML — no explanation, no markdown
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
    """Remove optional markdown code fences from a model response."""
    if not raw.startswith("```"):
        return raw
    lines = raw.split("\n")
    # Drop the opening fence line (e.g. ```json or ```)
    start = 1
    # Drop the closing fence if present
    end = len(lines)
    if lines and lines[-1].strip() == "```":
        end -= 1
    return "\n".join(lines[start:end]).strip()


async def generate_blog(
    brain_dump: str,
    brand_voice_profile: dict | None,
    thinking_tokens: int = 512,
) -> str:
    """Call Gemini 2.5 Flash to produce a semantic HTML blog post.

    Args:
        brain_dump: The author's raw idea text.
        brand_voice_profile: BVP dict or None (falls back to default voice).
        thinking_tokens: Gemini thinking token budget (512 per NFR-9).

    Returns:
        Raw HTML string of the blog post (markdown fences stripped).
    """
    if brand_voice_profile:
        bvp_json = json.dumps(brand_voice_profile)
        tone_list = ", ".join(brand_voice_profile.get("tone", []))
        cadence = brand_voice_profile.get("cadence", {})
        avg_sentence_length = cadence.get("avg_sentence_length", 15)
        banned_jargon_list = ", ".join(brand_voice_profile.get("banned_jargon", []))
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

    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        generation_config={"thinking_budget": thinking_tokens},
    )
    response = await model.generate_content_async(prompt)
    raw = response.text.strip()
    return _strip_fences(raw)


async def check_fidelity(
    blog_html: str,
    brand_voice_profile: dict | None,
    thinking_tokens: int = 256,
) -> dict:
    """Score blog HTML against the Brand Voice Profile.

    Args:
        blog_html: The generated blog post HTML.
        brand_voice_profile: BVP dict or None.
        thinking_tokens: Gemini thinking token budget (256 per NFR-9).

    Returns:
        Dict with keys: tone_score (int), cadence_score (int), jargon_violations (int).

    Raises:
        ValueError: If Gemini returns a response that cannot be parsed as the expected JSON.
    """
    if brand_voice_profile is None:
        return {"tone_score": 10, "cadence_score": 10, "jargon_violations": 0}

    prompt = _FIDELITY_PROMPT.format(
        bvp_json=json.dumps(brand_voice_profile),
        blog_html=blog_html,
    )

    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        generation_config={"thinking_budget": thinking_tokens},
    )
    response = await model.generate_content_async(prompt)
    raw = _strip_fences(response.text.strip())

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("check_fidelity: Gemini returned invalid JSON: %r", raw[:200])
        raise ValueError(f"check_fidelity: Gemini returned invalid JSON: {exc}") from exc

    for key in ("tone_score", "cadence_score", "jargon_violations"):
        if key not in data:
            raise ValueError(f"check_fidelity: missing key '{key}' in Gemini response")

    return data


async def generate_social(
    brain_dump: str,
    blog_title: str,
    brand_voice_profile: dict | None,
    thinking_tokens: int = 0,
) -> dict:
    """Generate X and LinkedIn posts from the brain dump and blog title.

    Args:
        brain_dump: The author's raw idea text.
        blog_title: Title extracted from the H1 of the blog post.
        brand_voice_profile: BVP dict or None (falls back to default voice).
        thinking_tokens: Gemini thinking token budget (0 per NFR-9 cost optimization).

    Returns:
        Dict with keys: x_post (str ≤280 chars), linkedin_post (str 500–1300 chars).

    Raises:
        ValueError: If Gemini returns a response that cannot be parsed as the expected JSON.
    """
    bvp_json = json.dumps(brand_voice_profile) if brand_voice_profile else _DEFAULT_VOICE

    prompt = _SOCIAL_PROMPT.format(
        bvp_json=bvp_json,
        brain_dump=brain_dump,
        blog_title=blog_title,
    )

    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        generation_config={"thinking_budget": thinking_tokens},
    )
    response = await model.generate_content_async(prompt)
    raw = _strip_fences(response.text.strip())

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("generate_social: Gemini returned invalid JSON: %r", raw[:200])
        raise ValueError(f"generate_social: Gemini returned invalid JSON: {exc}") from exc

    for key in ("x_post", "linkedin_post"):
        if key not in data:
            raise ValueError(f"generate_social: missing key '{key}' in Gemini response")

    for key in ("x_post", "linkedin_post"):
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
    if ln_len < 500 or ln_len > 1300:
        logger.warning(
            "generate_social: LinkedIn post length %d is outside expected 500–1300 chars",
            ln_len,
        )

    return data
