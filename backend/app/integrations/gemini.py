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
