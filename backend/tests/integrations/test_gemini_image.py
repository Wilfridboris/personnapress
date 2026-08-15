"""Unit tests for integrations/gemini_image.py."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_generated_image(image_bytes: bytes = b"fake-png-bytes"):
    image = MagicMock()
    image.image.image_data = image_bytes
    return image


def _make_response(images=None):
    response = MagicMock()
    response.generated_images = images if images is not None else [_make_generated_image()]
    return response


@pytest.mark.asyncio
async def test_gemini_image_uses_1_1_aspect_ratio():
    """Gemini Imagen call must use aspectRatio='1:1' (not '16:9').

    Since google.genai.types is a MagicMock stub in tests, we patch
    app.integrations.gemini_image.types and inspect the GenerateImagesConfig
    constructor kwargs directly.
    """
    fake_aio_models = MagicMock()
    fake_aio_models.generate_images = AsyncMock(return_value=_make_response())

    fake_aio = MagicMock()
    fake_aio.models = fake_aio_models

    fake_client = MagicMock()
    fake_client.aio = fake_aio

    mock_types = MagicMock()

    with (
        patch("app.integrations.gemini_image._client", fake_client),
        patch("app.integrations.gemini_image._MODEL", "imagen-3.0-generate-001"),
        patch("app.integrations.gemini_image.types", mock_types),
    ):
        from app.integrations.gemini_image import generate_image

        await generate_image("Test prompt")

    _, kwargs = mock_types.GenerateImagesConfig.call_args
    assert kwargs["aspectRatio"] == "1:1"


@pytest.mark.asyncio
async def test_gemini_image_raises_on_empty_response():
    """Empty generated_images list raises ValueError (safety filter guard)."""
    fake_aio_models = MagicMock()
    fake_aio_models.generate_images = AsyncMock(return_value=_make_response(images=[]))

    fake_aio = MagicMock()
    fake_aio.models = fake_aio_models

    fake_client = MagicMock()
    fake_client.aio = fake_aio

    with (
        patch("app.integrations.gemini_image._client", fake_client),
        patch("app.integrations.gemini_image._MODEL", "imagen-3.0-generate-001"),
    ):
        from app.integrations.gemini_image import generate_image

        with pytest.raises(ValueError, match="no images"):
            await generate_image("Test prompt")
