"""Replicate integration for FLUX.1 [pro] image generation.

Called ONLY from services/image.py (AR-19).
"""

import logging
from typing import Any

import replicate

logger = logging.getLogger(__name__)

_FLUX_MODEL = "black-forest-labs/flux-pro"


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
    output: Any = await replicate.async_run(
        _FLUX_MODEL,
        input={
            "prompt": prompt,
            "width": width,
            "height": height,
            "output_format": "png",
        },
    )
    # output is a list of FileOutput objects or URL strings
    image_url = str(output[0])
    logger.info("replicate.generate_image: received URL %s", image_url[:60])
    return image_url
