"""Unit tests for workers/ingest.py — questionnaire_worker()."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_job(job_id=None, status="pending"):
    j = MagicMock()
    j.id = job_id or uuid.uuid4()
    j.status = status
    j.started_at = None
    j.completed_at = None
    j.error_details = None
    return j


def _db_sequence(*values):
    db = AsyncMock()
    results = []
    for v in values:
        r = MagicMock()
        r.scalar_one_or_none.return_value = v
        results.append(r)
    db.execute = AsyncMock(side_effect=results)
    return db


def _make_questionnaire_data(
    formal_casual=3,
    professional_friendly=3,
    concise_elaborate=3,
    sample_texts=None,
    reference_urls=None,
):
    from app.schemas.client import QuestionnaireRequest

    return QuestionnaireRequest(
        tone_sliders={
            "formal_casual": formal_casual,
            "professional_friendly": professional_friendly,
            "concise_elaborate": concise_elaborate,
        },
        sample_texts=sample_texts or [],
        reference_urls=reference_urls or [],
    )


# ── Slider tone descriptor conversion ─────────────────────────────────────────

def test_sliders_to_tone_descriptors_maps_all_values():
    from app.workers.ingest import _sliders_to_tone_descriptors
    from app.schemas.client import ToneSliders

    result = _sliders_to_tone_descriptors(ToneSliders(
        formal_casual=1,
        professional_friendly=5,
        concise_elaborate=3,
    ))
    assert "formal" in result
    assert "warm" in result
    assert "balanced" in result


def test_sliders_to_tone_descriptors_returns_three_descriptors():
    from app.workers.ingest import _sliders_to_tone_descriptors
    from app.schemas.client import ToneSliders

    # All valid values in 1–5 range produce exactly 3 descriptors
    result = _sliders_to_tone_descriptors(ToneSliders(
        formal_casual=2,
        professional_friendly=4,
        concise_elaborate=5,
    ))
    assert isinstance(result, list)
    assert len(result) == 3


def test_sliders_to_tone_descriptors_maps_boundary_values():
    from app.workers.ingest import _sliders_to_tone_descriptors
    from app.schemas.client import ToneSliders

    result = _sliders_to_tone_descriptors(ToneSliders(
        formal_casual=5,
        professional_friendly=1,
        concise_elaborate=1,
    ))
    assert "casual" in result
    assert "professional" in result
    assert "concise" in result


# ── questionnaire_worker: job not found ───────────────────────────────────────

@pytest.mark.asyncio
@patch("app.workers.ingest.AsyncSessionLocal")
async def test_questionnaire_worker_job_not_found_returns_early(mock_session_cls):
    from app.workers.ingest import questionnaire_worker

    db = _db_sequence(None)  # job lookup returns None
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_session_cls.return_value = ctx

    questionnaire_data = _make_questionnaire_data()

    await questionnaire_worker(uuid.uuid4(), uuid.uuid4(), questionnaire_data)

    db.commit.assert_not_called()


# ── questionnaire_worker: no text provided ────────────────────────────────────

@pytest.mark.asyncio
@patch("app.workers.ingest._sliders_to_tone_descriptors", return_value=[])
@patch("app.workers.ingest.AsyncSessionLocal")
async def test_questionnaire_worker_no_content_marks_failed(mock_session_cls, mock_sliders):
    from app.workers.ingest import questionnaire_worker

    job_id = uuid.uuid4()
    job = _make_job(job_id=job_id)

    db = _db_sequence(job)
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_session_cls.return_value = ctx

    # No tone descriptors (mocked), no texts, no URLs → no content
    questionnaire_data = _make_questionnaire_data()

    await questionnaire_worker(job_id, uuid.uuid4(), questionnaire_data)

    assert job.status == "failed"
    assert job.error_details is not None


# ── questionnaire_worker: success path ───────────────────────────────────────

@pytest.mark.asyncio
@patch("app.workers.ingest.extract_voice_profile", new_callable=AsyncMock)
@patch("app.workers.ingest.AsyncSessionLocal")
async def test_questionnaire_worker_success_sets_completed(
    mock_session_cls,
    mock_extract,
):
    from app.workers.ingest import questionnaire_worker

    job_id = uuid.uuid4()
    client_id = uuid.uuid4()
    job = _make_job(job_id=job_id)

    db = _db_sequence(job)
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_session_cls.return_value = ctx

    mock_extract.return_value = {
        "tone": ["professional"],
        "cadence": {"avg_sentence_length": 15, "variation_pattern": "", "paragraph_structure": ""},
        "banned_jargon": [],
    }

    questionnaire_data = _make_questionnaire_data(
        formal_casual=2,
        sample_texts=["This is my writing style."],
    )

    await questionnaire_worker(job_id, client_id, questionnaire_data)

    assert job.status == "complete"
    assert job.completed_at is not None
    mock_extract.assert_called_once()


# ── questionnaire_worker: extraction failure ──────────────────────────────────

@pytest.mark.asyncio
@patch("app.workers.ingest.extract_voice_profile", new_callable=AsyncMock)
@patch("app.workers.ingest.AsyncSessionLocal")
async def test_questionnaire_worker_extraction_failure_marks_failed(
    mock_session_cls,
    mock_extract,
):
    from app.workers.ingest import questionnaire_worker
    from app.services.ingestion import VoiceExtractionError

    job_id = uuid.uuid4()
    job = _make_job(job_id=job_id)

    db = _db_sequence(job)
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_session_cls.return_value = ctx

    mock_extract.side_effect = VoiceExtractionError("Gemini failed after 3 retries")

    questionnaire_data = _make_questionnaire_data(sample_texts=["Some text here"])

    await questionnaire_worker(job_id, uuid.uuid4(), questionnaire_data)

    assert job.status == "failed"
    assert job.error_details is not None


# ── questionnaire_worker: builds combined text from slider + samples ──────────

@pytest.mark.asyncio
@patch("app.workers.ingest.extract_voice_profile", new_callable=AsyncMock)
@patch("app.workers.ingest.AsyncSessionLocal")
async def test_questionnaire_worker_includes_samples_in_text(
    mock_session_cls,
    mock_extract,
):
    from app.workers.ingest import questionnaire_worker

    job_id = uuid.uuid4()
    job = _make_job(job_id=job_id)

    db = _db_sequence(job)
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_session_cls.return_value = ctx

    mock_extract.return_value = {"tone": [], "cadence": {}, "banned_jargon": []}

    sample = "I write with a casual, friendly voice."
    questionnaire_data = _make_questionnaire_data(sample_texts=[sample])

    await questionnaire_worker(job_id, uuid.uuid4(), questionnaire_data)

    called_args = mock_extract.call_args
    combined_text = called_args[0][0]
    assert sample in combined_text


# ── questionnaire_worker: marks in-progress first ────────────────────────────

@pytest.mark.asyncio
@patch("app.workers.ingest.extract_voice_profile", new_callable=AsyncMock)
@patch("app.workers.ingest.AsyncSessionLocal")
async def test_questionnaire_worker_sets_in_progress_first(
    mock_session_cls,
    mock_extract,
):
    from app.workers.ingest import questionnaire_worker

    job_id = uuid.uuid4()
    job = _make_job(job_id=job_id)
    statuses: list[str] = []

    db = _db_sequence(job)
    original_commit = db.commit

    async def track_commit():
        statuses.append(job.status)
        await original_commit()

    db.commit = track_commit
    db.refresh = AsyncMock()

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_session_cls.return_value = ctx

    mock_extract.return_value = {"tone": [], "cadence": {}, "banned_jargon": []}

    questionnaire_data = _make_questionnaire_data(sample_texts=["some text"])
    await questionnaire_worker(job_id, uuid.uuid4(), questionnaire_data)

    assert "in_progress" in statuses
    assert statuses[0] == "in_progress"


# ── Gap-fill: reference URLs included in combined text ───────────────────────

@pytest.mark.asyncio
@patch("app.workers.ingest.extract_voice_profile", new_callable=AsyncMock)
@patch("app.workers.ingest.AsyncSessionLocal")
async def test_questionnaire_worker_includes_reference_urls_in_combined_text(
    mock_session_cls,
    mock_extract,
):
    """Reference writer URLs provided in Step 3 must appear in the text sent to Gemini."""
    from app.workers.ingest import questionnaire_worker

    job_id = uuid.uuid4()
    job = _make_job(job_id=job_id)

    db = _db_sequence(job)
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_session_cls.return_value = ctx

    mock_extract.return_value = {"tone": [], "cadence": {}, "banned_jargon": []}

    reference_url = "https://paulgraham.com"
    questionnaire_data = _make_questionnaire_data(
        formal_casual=3,
        sample_texts=["Some writing sample."],
        reference_urls=[reference_url],
    )

    await questionnaire_worker(job_id, uuid.uuid4(), questionnaire_data)

    combined_text = mock_extract.call_args[0][0]
    assert reference_url in combined_text


# ── Gap-fill: sliders only (no sample texts, no URLs) ────────────────────────

@pytest.mark.asyncio
@patch("app.workers.ingest.extract_voice_profile", new_callable=AsyncMock)
@patch("app.workers.ingest.AsyncSessionLocal")
async def test_questionnaire_worker_tone_sliders_only_succeeds(
    mock_session_cls,
    mock_extract,
):
    """Step 1 (tone sliders) alone — with no sample texts or URLs — is valid and completes."""
    from app.workers.ingest import questionnaire_worker

    job_id = uuid.uuid4()
    job = _make_job(job_id=job_id)

    db = _db_sequence(job)
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_session_cls.return_value = ctx

    mock_extract.return_value = {"tone": ["formal"], "cadence": {}, "banned_jargon": []}

    # Only slider values — no texts, no URLs
    questionnaire_data = _make_questionnaire_data(
        formal_casual=1,
        professional_friendly=1,
        concise_elaborate=1,
    )

    await questionnaire_worker(job_id, uuid.uuid4(), questionnaire_data)

    assert job.status == "complete"
    combined_text = mock_extract.call_args[0][0]
    assert "TONE CONTEXT" in combined_text
