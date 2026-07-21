"""Native Gemini image generation integration.

Activated when IMAGE_PROVIDER=gemini. Uses the google-genai SDK (already a
project dependency). Called ONLY from services/image.py (AR-19).
"""

import logging

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)

_client = genai.Client(api_key=settings.GEMINI_API_KEY)
_MODEL = settings.IMAGE_MODEL  # e.g. "imagen-3.0-generate-001"


async def generate_image(prompt: str, width: int = 1200, height: int = 630) -> bytes:
    """Generate image via Gemini Imagen API. Returns raw PNG bytes.

    NOTE: width/height are unused — Gemini controls dimensions via aspect_ratio only.
    NOTE: The Gemini Imagen API returns image bytes, not a URL. The caller
    (services/image.py) must upload these bytes directly to Supabase Storage
    rather than using upload_image_from_url().
    """
    logger.info("gemini_image.generate_image: calling %s (prompt len=%d)", _MODEL, len(prompt))
    response = await _client.aio.models.generate_images(
        model=_MODEL,
        prompt=prompt,
        config=types.GenerateImagesConfig(
            numberOfImages=1,
            aspectRatio="16:9",
            outputMimeType="image/png",
        ),
    )
    if not response.generated_images:
        raise ValueError(
            f"Gemini image generation returned no images for model {_MODEL!r} "
            "(likely blocked by safety filter)"
        )
    image_bytes: bytes = response.generated_images[0].image.image_data
    logger.info("gemini_image.generate_image: received %d bytes", len(image_bytes))
    return image_bytes
