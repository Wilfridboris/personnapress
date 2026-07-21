"""Replicate image generation integration.

Model and schema are controlled by IMAGE_MODEL / IMAGE_PROVIDER settings.
Called ONLY from services/image.py (AR-19).
"""

import logging
from typing import Any

import replicate

from app.core.config import settings

logger = logging.getLogger(__name__)

_MODEL = settings.IMAGE_MODEL
_IS_FLUX = _MODEL.startswith("black-forest-labs/")

_client = replicate.Client(api_token=settings.REPLICATE_API_TOKEN)


async def generate_image(prompt: str, width: int = 1200, height: int = 630) -> str:
    """Call the configured Replicate model and return the temporary image URL.

    Args:
        prompt: Visual description prompt for the image.
        width: Output image width in pixels (used only in FLUX branch).
        height: Output image height in pixels (used only in FLUX branch).

    Returns:
        Temporary Replicate CDN URL string.

    Raises:
        Exception: Re-raises any Replicate SDK error for the caller to handle.
    """
    logger.info("replicate.generate_image: calling %s (prompt len=%d)", _MODEL, len(prompt))

    if _IS_FLUX:
        input_payload: dict[str, Any] = {
            "prompt": prompt,
            "aspect_ratio": "custom",
            "width": width,
            "height": height,
            "output_format": "png",
            "output_quality": 100,
            "safety_tolerance": 2,
        }
    else:
        # Nano Banana Pro (and other non-FLUX Replicate models)
        input_payload = {
            "prompt": prompt,
            "aspect_ratio": "16:9",
            "output_format": "png",
        }

    output: Any = await _client.async_run(_MODEL, input=input_payload)
    # output is a FileOutput object or a list — normalise either case
    if isinstance(output, (list, tuple)) and not output:
        raise ValueError("Replicate returned empty output list")
    image_url = str(output[0] if isinstance(output, (list, tuple)) else output)
    logger.info("replicate.generate_image: received URL %s", image_url[:60])
    return image_url
