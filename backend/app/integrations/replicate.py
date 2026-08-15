"""Replicate image generation integration.

Model and schema are controlled by IMAGE_MODEL / IMAGE_PROVIDER settings.
Called ONLY from services/image.py (AR-19).
"""

import asyncio
import logging
from typing import Any

import replicate

from app.core.config import settings

logger = logging.getLogger(__name__)

_MODEL = settings.IMAGE_MODEL
_IS_FLUX = _MODEL.startswith("black-forest-labs/")

_client = replicate.Client(api_token=settings.REPLICATE_API_TOKEN)


async def generate_image(prompt: str, width: int = 1080, height: int = 1080) -> str:
    """Call the configured Replicate model and return the temporary image URL.

    Args:
        prompt: Visual description prompt for the image.
        width: Output image width in pixels (used only in FLUX branch).
        height: Output image height in pixels (used only in FLUX branch).

    Returns:
        Temporary Replicate CDN URL string.

    Raises:
        asyncio.TimeoutError: If the prediction takes longer than 120 seconds (after cancel).
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
            "aspect_ratio": "1:1",
            "output_format": "png",
        }

    prediction = await _client.predictions.async_create(model=_MODEL, input=input_payload)
    logger.info(
        "replicate.generate_image: prediction %s started (model=%s)", prediction.id, _MODEL
    )

    try:
        await asyncio.wait_for(prediction.async_wait(), timeout=120.0)
    except asyncio.TimeoutError:
        try:
            await asyncio.wait_for(prediction.async_cancel(), timeout=10.0)
            logger.info(
                "replicate.generate_image: cancelled hung prediction %s", prediction.id
            )
        except Exception as cancel_exc:
            logger.warning(
                "replicate.generate_image: could not cancel prediction %s: %s",
                prediction.id,
                cancel_exc,
            )
        raise

    if prediction.status == "failed":
        raise ValueError(f"Replicate prediction {prediction.id} failed: {prediction.error}")
    if prediction.status == "canceled":
        raise ValueError(f"Replicate prediction {prediction.id} was canceled externally")

    output = prediction.output
    if output is None:
        raise ValueError("Replicate returned None output")
    if isinstance(output, (list, tuple)) and not output:
        raise ValueError("Replicate returned empty output list")
    image_url = str(output[0] if isinstance(output, (list, tuple)) else output)
    logger.info("replicate.generate_image: received URL %s", image_url[:60])
    return image_url
