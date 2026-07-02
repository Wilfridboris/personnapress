"""Replicate integration for FLUX.1 [pro] image generation.

Called ONLY from services/image.py (AR-19).
"""

import logging
from typing import Any

import replicate

from app.core.config import settings

logger = logging.getLogger(__name__)

_FLUX_MODEL = "black-forest-labs/flux-pro"

_client = replicate.Client(api_token=settings.REPLICATE_API_TOKEN)


async def generate_image(prompt: str, width: int = 1200, height: int = 630) -> str:
    """Call FLUX.1 [pro] on Replicate and return the temporary image URL.

    Args:
        prompt: Visual description prompt for the image.
        width: Output image width in pixels (default 1200 for OG).
        height: Output image height in pixels (default 630 for OG).

    Returns:
        Temporary Replicate CDN URL string.

    Raises:
        Exception: Re-raises any Replicate SDK error for the caller to handle.
    """
    logger.info("replicate.generate_image: calling %s (prompt len=%d)", _FLUX_MODEL, len(prompt))
    output: Any = await _client.async_run(
        _FLUX_MODEL,
        input={
            "prompt": prompt,
            "width": width,
            "height": height,
            "output_format": "png",
        },
    )
    # output is a FileOutput object or a list — normalise either case
    image_url = str(output[0] if isinstance(output, (list, tuple)) else output)
    logger.info("replicate.generate_image: received URL %s", image_url[:60])
    return image_url
