"""Unit tests for services/ingestion.py — extract_voice_profile() retry logic."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest


_VALID_BVP = {
    "tone": ["professional", "concise"],
    "cadence": {
        "avg_sentence_length": 15,
        "variation_pattern": "consistent",
        "paragraph_structure": "3-4 sentences",
    },
    "banned_jargon": ["synergy"],
}


# ── Happy path ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.services.ingestion.update_client", new_callable=AsyncMock)
@patch("app.services.ingestion.asyncio.sleep", new_callable=AsyncMock)
@patch("app.services.ingestion.gemini")
async def test_extract_voice_profile_success_on_first_attempt(
    mock_gemini, mock_sleep, mock_update_client
):
    from app.services.ingestion import extract_voice_profile

    mock_gemini.extract_brand_voice = AsyncMock(return_value=_VALID_BVP)
    mock_session = AsyncMock()

    result = await extract_voice_profile("Brand text", uuid.uuid4(), session=mock_session)

    assert result == _VALID_BVP
    mock_gemini.extract_brand_voice.assert_called_once()
    mock_sleep.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.ingestion.update_client", new_callable=AsyncMock)
@patch("app.services.ingestion.asyncio.sleep", new_callable=AsyncMock)
@patch("app.services.ingestion.gemini")
async def test_extract_voice_profile_updates_client_on_success(
    mock_gemini, mock_sleep, mock_update_client
):
    from app.services.ingestion import extract_voice_profile

    mock_gemini.extract_brand_voice = AsyncMock(return_value=_VALID_BVP)
    mock_session = AsyncMock()
    client_id = uuid.uuid4()

    await extract_voice_profile("Brand text", client_id, session=mock_session)

    mock_update_client.assert_called_once_with(
        mock_session, client_id, brand_voice_profile=_VALID_BVP
    )


@pytest.mark.asyncio
@patch("app.services.ingestion.update_client", new_callable=AsyncMock)
@patch("app.services.ingestion.asyncio.sleep", new_callable=AsyncMock)
@patch("app.services.ingestion.gemini")
async def test_extract_voice_profile_no_session_skips_db_update(
    mock_gemini, mock_sleep, mock_update_client
):
    from app.services.ingestion import extract_voice_profile

    mock_gemini.extract_brand_voice = AsyncMock(return_value=_VALID_BVP)

    result = await extract_voice_profile("Brand text", uuid.uuid4(), session=None)

    assert result == _VALID_BVP
    mock_update_client.assert_not_called()


# ── Retry logic ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.services.ingestion.update_client", new_callable=AsyncMock)
@patch("app.services.ingestion.asyncio.sleep", new_callable=AsyncMock)
@patch("app.services.ingestion.gemini")
async def test_extract_voice_profile_retries_on_failure_then_succeeds(
    mock_gemini, mock_sleep, mock_update_client
):
    from app.services.ingestion import extract_voice_profile

    # Fail twice with transient errors, succeed on third attempt
    mock_gemini.extract_brand_voice = AsyncMock(
        side_effect=[RuntimeError("API error"), RuntimeError("timeout"), _VALID_BVP]
    )
    mock_session = AsyncMock()

    result = await extract_voice_profile("Brand text", uuid.uuid4(), session=mock_session)

    assert result == _VALID_BVP
    assert mock_gemini.extract_brand_voice.call_count == 3
    # Two sleeps between attempts: 1s (2^0), 2s (2^1)
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(1)
    mock_sleep.assert_any_call(2)


@pytest.mark.asyncio
@patch("app.services.ingestion.sentry_sdk")
@patch("app.services.ingestion.asyncio.sleep", new_callable=AsyncMock)
@patch("app.services.ingestion.gemini")
async def test_extract_voice_profile_raises_after_3_failures(
    mock_gemini, mock_sleep, mock_sentry
):
    from app.services.ingestion import extract_voice_profile, VoiceExtractionError

    error = RuntimeError("Gemini 500")
    mock_gemini.extract_brand_voice = AsyncMock(side_effect=error)

    with pytest.raises(VoiceExtractionError):
        await extract_voice_profile("Brand text", uuid.uuid4(), session=None)

    assert mock_gemini.extract_brand_voice.call_count == 3
    mock_sentry.capture_exception.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.ingestion.sentry_sdk")
@patch("app.services.ingestion.asyncio.sleep", new_callable=AsyncMock)
@patch("app.services.ingestion.gemini")
async def test_extract_voice_profile_logs_to_sentry_on_failure(
    mock_gemini, mock_sleep, mock_sentry
):
    from app.services.ingestion import extract_voice_profile, VoiceExtractionError

    mock_gemini.extract_brand_voice = AsyncMock(side_effect=RuntimeError("503 error"))

    try:
        await extract_voice_profile("text", uuid.uuid4(), session=None)
    except VoiceExtractionError:
        pass

    mock_sentry.capture_exception.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.ingestion.sentry_sdk")
@patch("app.services.ingestion.asyncio.sleep", new_callable=AsyncMock)
@patch("app.services.ingestion.gemini")
async def test_extract_voice_profile_exponential_backoff(
    mock_gemini, mock_sleep, mock_sentry
):
    """Sleep intervals must be 1s and 2s (2^0, 2^1) between the three attempts."""
    from app.services.ingestion import extract_voice_profile, VoiceExtractionError

    mock_gemini.extract_brand_voice = AsyncMock(side_effect=RuntimeError("error"))

    try:
        await extract_voice_profile("text", uuid.uuid4(), session=None)
    except VoiceExtractionError:
        pass

    assert mock_sleep.call_count == 2
    calls = [c.args[0] for c in mock_sleep.call_args_list]
    assert calls == [1, 2]


# ── VoiceExtractionError ──────────────────────────────────────────────────────

def test_voice_extraction_error_is_exception():
    from app.services.ingestion import VoiceExtractionError

    err = VoiceExtractionError("Gemini failed after 3 retries")
    assert isinstance(err, Exception)
    assert "Gemini failed" in str(err)
