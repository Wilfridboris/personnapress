"""Unit tests for integrations/replicate.py — model schema branching."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model,expected_aspect_ratio,expect_width_height",
    [
        ("google/nano-banana-pro", "16:9", False),
        ("black-forest-labs/flux-1.1-pro", "custom", True),
    ],
)
async def test_generate_image_input_schema_by_model(
    model, expected_aspect_ratio, expect_width_height
):
    """Model family determines input schema: Nano Banana → 16:9; FLUX → custom + dimensions."""
    captured_input: dict = {}

    async def fake_async_run(model_id, input):
        captured_input.update(input)
        return "https://replicate.delivery/test.png"

    fake_client = MagicMock()
    fake_client.async_run = fake_async_run

    with (
        patch("app.integrations.replicate.settings") as mock_settings,
        patch("app.integrations.replicate._client", fake_client),
        patch("app.integrations.replicate._MODEL", model),
        patch("app.integrations.replicate._IS_FLUX", model.startswith("black-forest-labs/")),
    ):
        mock_settings.IMAGE_MODEL = model
        mock_settings.REPLICATE_API_TOKEN = "r8_test"

        from app.integrations.replicate import generate_image

        result = await generate_image("Test prompt")

    assert result == "https://replicate.delivery/test.png"
    assert captured_input["aspect_ratio"] == expected_aspect_ratio

    if expect_width_height:
        assert "width" in captured_input
        assert "height" in captured_input
        assert captured_input["width"] == 1200
        assert captured_input["height"] == 630
    else:
        assert "width" not in captured_input
        assert "height" not in captured_input
