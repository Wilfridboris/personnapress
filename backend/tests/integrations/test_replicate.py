"""Unit tests for integrations/replicate.py — model schema branching + cancel-on-timeout."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_prediction(prediction_id="pred_abc123", status="succeeded", output=None):
    prediction = MagicMock()
    prediction.id = prediction_id
    prediction.status = status
    prediction.output = output or "https://replicate.delivery/test.png"
    prediction.error = None
    prediction.async_wait = AsyncMock()
    prediction.async_cancel = AsyncMock()
    return prediction


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

    prediction = _make_prediction(output="https://replicate.delivery/test.png")

    async def fake_async_create(model=None, input=None, **kwargs):
        captured_input.update(input or {})
        return prediction

    fake_predictions = MagicMock()
    fake_predictions.async_create = fake_async_create

    fake_client = MagicMock()
    fake_client.predictions = fake_predictions

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


@pytest.mark.asyncio
async def test_generate_image_cancels_hung_prediction_on_timeout():
    """When async_wait times out after 120s, async_cancel is called before re-raising."""
    prediction = _make_prediction()
    prediction.async_wait = AsyncMock(side_effect=asyncio.TimeoutError())

    async def fake_async_create(model=None, input=None, **kwargs):
        return prediction

    fake_predictions = MagicMock()
    fake_predictions.async_create = fake_async_create

    fake_client = MagicMock()
    fake_client.predictions = fake_predictions

    with (
        patch("app.integrations.replicate._client", fake_client),
        patch("app.integrations.replicate._MODEL", "google/nano-banana-pro"),
        patch("app.integrations.replicate._IS_FLUX", False),
        patch("app.integrations.replicate.asyncio.wait_for", side_effect=asyncio.TimeoutError()),
    ):
        from app.integrations.replicate import generate_image

        with pytest.raises(asyncio.TimeoutError):
            await generate_image("Test prompt")

    prediction.async_cancel.assert_called_once()


@pytest.mark.asyncio
async def test_generate_image_cancel_failure_does_not_suppress_timeout():
    """If async_cancel raises, the TimeoutError is still re-raised (no swallowing)."""
    prediction = _make_prediction()
    prediction.async_cancel = AsyncMock(side_effect=Exception("cancel failed"))

    async def fake_async_create(model=None, input=None, **kwargs):
        return prediction

    fake_predictions = MagicMock()
    fake_predictions.async_create = fake_async_create

    fake_client = MagicMock()
    fake_client.predictions = fake_predictions

    with (
        patch("app.integrations.replicate._client", fake_client),
        patch("app.integrations.replicate._MODEL", "google/nano-banana-pro"),
        patch("app.integrations.replicate._IS_FLUX", False),
        patch("app.integrations.replicate.asyncio.wait_for", side_effect=asyncio.TimeoutError()),
    ):
        from app.integrations.replicate import generate_image

        with pytest.raises(asyncio.TimeoutError):
            await generate_image("Test prompt")


@pytest.mark.asyncio
async def test_generate_image_raises_on_failed_prediction():
    """Prediction with status='failed' raises ValueError."""
    prediction = _make_prediction(status="failed")
    prediction.error = "GPU out of memory"

    async def fake_async_create(model=None, input=None, **kwargs):
        return prediction

    fake_predictions = MagicMock()
    fake_predictions.async_create = fake_async_create

    fake_client = MagicMock()
    fake_client.predictions = fake_predictions

    with (
        patch("app.integrations.replicate._client", fake_client),
        patch("app.integrations.replicate._MODEL", "google/nano-banana-pro"),
        patch("app.integrations.replicate._IS_FLUX", False),
    ):
        from app.integrations.replicate import generate_image

        with pytest.raises(ValueError, match="failed"):
            await generate_image("Test prompt")


@pytest.mark.asyncio
async def test_generate_image_raises_on_none_output():
    """Prediction with status='succeeded' but output=None raises ValueError."""
    prediction = _make_prediction(status="succeeded", output=None)
    prediction.output = None

    async def fake_async_create(model=None, input=None, **kwargs):
        return prediction

    fake_predictions = MagicMock()
    fake_predictions.async_create = fake_async_create

    fake_client = MagicMock()
    fake_client.predictions = fake_predictions

    with (
        patch("app.integrations.replicate._client", fake_client),
        patch("app.integrations.replicate._MODEL", "google/nano-banana-pro"),
        patch("app.integrations.replicate._IS_FLUX", False),
    ):
        from app.integrations.replicate import generate_image

        with pytest.raises(ValueError, match="None output"):
            await generate_image("Test prompt")
