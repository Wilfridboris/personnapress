"""Unit tests for Story 2.5 router endpoints.

Covers:
- POST /clients/{id}/questionnaire (AC #6)
- GET /clients/{id} — ingestion_failed / ingestion_error state fields (AC #4, #5, #8)
- PATCH /clients/{id} with brand_voice_profile update (AC #3, Task 8)
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.schemas.client import ClientUpdate, QuestionnaireRequest

# Ensure app.routers.clients is importable (stripe stub is in conftest.py)
import app.routers.clients  # noqa: F401 — makes @patch resolution work


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_client(user_id=None, bvp=None, url=None):
    c = MagicMock()
    c.id = uuid.uuid4()
    c.user_id = user_id or uuid.uuid4()
    c.name = "Acme Corp"
    c.website_url = url
    c.brand_voice_profile = bvp
    c.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return c


def _make_job(status="pending", error_details=None):
    j = MagicMock()
    j.id = uuid.uuid4()
    j.status = status
    j.error_details = error_details
    return j


def _questionnaire_payload():
    return QuestionnaireRequest(
        tone_sliders={"formal_casual": 3, "professional_friendly": 4, "concise_elaborate": 2},
        sample_texts=["This is how I write. Short sentences. Direct."],
        reference_urls=[],
    )


# ═══════════════════════════════════════════════════════════════════════════════
# POST /clients/{client_id}/questionnaire  (AC #6)
# ═══════════════════════════════════════════════════════════════════════════════

@patch("app.routers.clients.create_job")
@patch("app.routers.clients.get_active_ingestion_job_for_client")
@patch("app.routers.clients.get_client")
async def test_submit_questionnaire_happy_path_returns_202_job_id(
    mock_get_client, mock_active_job, mock_create_job
):
    """Happy path: returns {"job_id": str(job.id)} with HTTP 202 semantics."""
    from app.routers.clients import submit_voice_questionnaire

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    job = _make_job()
    mock_get_client.return_value = client
    mock_active_job.return_value = None
    mock_create_job.return_value = job
    current_user = {"user_id": str(user_id)}
    db = AsyncMock()
    bg = MagicMock()

    result = await submit_voice_questionnaire(
        client.id, _questionnaire_payload(), bg, current_user, db
    )

    assert result == {"job_id": str(job.id)}
    db.commit.assert_called_once()


@patch("app.routers.clients.get_client")
async def test_submit_questionnaire_invalid_session_returns_401(mock_get_client):
    """Missing user_id in session raises 401."""
    from app.routers.clients import submit_voice_questionnaire

    db = AsyncMock()
    bg = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await submit_voice_questionnaire(
            uuid.uuid4(), _questionnaire_payload(), bg, {}, db
        )

    assert exc_info.value.status_code == 401


@patch("app.routers.clients.get_client")
async def test_submit_questionnaire_client_not_found_returns_404(mock_get_client):
    """Non-existent client returns 404."""
    from app.routers.clients import submit_voice_questionnaire

    mock_get_client.return_value = None
    current_user = {"user_id": str(uuid.uuid4())}
    db = AsyncMock()
    bg = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await submit_voice_questionnaire(
            uuid.uuid4(), _questionnaire_payload(), bg, current_user, db
        )

    assert exc_info.value.status_code == 404


@patch("app.routers.clients.get_client")
async def test_submit_questionnaire_wrong_owner_returns_403(mock_get_client):
    """Client owned by a different user returns 403."""
    from app.routers.clients import submit_voice_questionnaire

    owner_id = uuid.uuid4()
    requester_id = uuid.uuid4()
    client = _make_client(user_id=owner_id)
    mock_get_client.return_value = client
    current_user = {"user_id": str(requester_id)}
    db = AsyncMock()
    bg = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await submit_voice_questionnaire(
            client.id, _questionnaire_payload(), bg, current_user, db
        )

    assert exc_info.value.status_code == 403


@patch("app.routers.clients.create_job")
@patch("app.routers.clients.get_active_ingestion_job_for_client")
@patch("app.routers.clients.get_client")
async def test_submit_questionnaire_dispatches_questionnaire_worker(
    mock_get_client, mock_active_job, mock_create_job
):
    """BackgroundTask is dispatched with job_id, client_id, and questionnaire_data."""
    from app.routers.clients import submit_voice_questionnaire

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    job = _make_job()
    mock_get_client.return_value = client
    mock_active_job.return_value = None
    mock_create_job.return_value = job
    current_user = {"user_id": str(user_id)}
    db = AsyncMock()
    bg = MagicMock()

    payload = _questionnaire_payload()
    await submit_voice_questionnaire(client.id, payload, bg, current_user, db)

    bg.add_task.assert_called_once()
    kw = bg.add_task.call_args[1]
    assert kw["job_id"] == job.id
    assert kw["client_id"] == client.id
    assert kw["questionnaire_data"] is payload


@patch("app.routers.clients.create_job")
@patch("app.routers.clients.get_active_ingestion_job_for_client")
@patch("app.routers.clients.get_client")
async def test_submit_questionnaire_creates_questionnaire_type_job(
    mock_get_client, mock_active_job, mock_create_job
):
    """create_job is called with job_type='questionnaire', status='pending'."""
    from app.routers.clients import submit_voice_questionnaire

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    job = _make_job()
    mock_get_client.return_value = client
    mock_active_job.return_value = None
    mock_create_job.return_value = job
    current_user = {"user_id": str(user_id)}
    db = AsyncMock()
    bg = MagicMock()

    await submit_voice_questionnaire(client.id, _questionnaire_payload(), bg, current_user, db)

    mock_create_job.assert_called_once_with(
        db, job_type="questionnaire", status="pending", client_id=client.id
    )


# ═══════════════════════════════════════════════════════════════════════════════
# GET /clients/{client_id} — voice setup state fields  (AC #4, #5, #8)
# ═══════════════════════════════════════════════════════════════════════════════

@patch("app.routers.clients.get_client")
async def test_get_client_detail_invalid_session_returns_401(mock_get_client):
    """Missing user_id in session raises 401."""
    from app.routers.clients import get_client_detail

    db = AsyncMock()
    with pytest.raises(HTTPException) as exc_info:
        await get_client_detail(uuid.uuid4(), {}, db)
    assert exc_info.value.status_code == 401


@patch("app.routers.clients.get_client")
async def test_get_client_detail_not_found_returns_404(mock_get_client):
    """Non-existent client returns 404."""
    from app.routers.clients import get_client_detail

    mock_get_client.return_value = None
    current_user = {"user_id": str(uuid.uuid4())}
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await get_client_detail(uuid.uuid4(), current_user, db)
    assert exc_info.value.status_code == 404


@patch("app.routers.clients.get_campaign_count")
@patch("app.routers.clients.get_latest_voice_job_for_client")
@patch("app.routers.clients.get_active_ingestion_job_for_client")
@patch("app.routers.clients.get_client")
async def test_get_client_detail_wrong_owner_returns_404(
    mock_get_client, mock_active_job, mock_latest_job, mock_campaign_count
):
    """Client owned by a different user returns 404 (not 403) to avoid info leak."""
    from app.routers.clients import get_client_detail

    owner_id = uuid.uuid4()
    requester_id = uuid.uuid4()
    client = _make_client(user_id=owner_id)
    mock_get_client.return_value = client
    current_user = {"user_id": str(requester_id)}
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await get_client_detail(client.id, current_user, db)
    assert exc_info.value.status_code == 404


@patch("app.routers.clients.get_campaign_count")
@patch("app.routers.clients.get_latest_voice_job_for_client")
@patch("app.routers.clients.get_active_ingestion_job_for_client")
@patch("app.routers.clients.get_client")
async def test_get_client_detail_ingestion_failed_true_when_latest_job_failed(
    mock_get_client, mock_active_job, mock_latest_job, mock_campaign_count
):
    """ingestion_failed=True when active_job is None, latest_job is 'failed', BVP is None (AC #4)."""
    from app.routers.clients import get_client_detail

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id, bvp=None)
    failed_job = _make_job(status="failed", error_details="Gemini 500 after 3 retries")
    mock_get_client.return_value = client
    mock_active_job.return_value = None
    mock_latest_job.return_value = failed_job
    mock_campaign_count.return_value = 0
    current_user = {"user_id": str(user_id)}
    db = AsyncMock()

    result = await get_client_detail(client.id, current_user, db)

    assert result.ingestion_failed is True
    assert result.ingestion_error == "Gemini 500 after 3 retries"


@patch("app.routers.clients.get_campaign_count")
@patch("app.routers.clients.get_latest_voice_job_for_client")
@patch("app.routers.clients.get_active_ingestion_job_for_client")
@patch("app.routers.clients.get_client")
async def test_get_client_detail_ingestion_failed_false_when_bvp_exists(
    mock_get_client, mock_active_job, mock_latest_job, mock_campaign_count
):
    """ingestion_failed=False when client already has a confirmed BVP (AC #8)."""
    from app.routers.clients import get_client_detail

    user_id = uuid.uuid4()
    bvp = {
        "tone": ["professional", "concise"],
        "cadence": {"avg_sentence_length": 15, "variation_pattern": "short", "paragraph_structure": "3-4"},
        "banned_jargon": ["leverage"],
    }
    client = _make_client(user_id=user_id, bvp=bvp)
    failed_job = _make_job(status="failed")
    mock_get_client.return_value = client
    mock_active_job.return_value = None
    mock_latest_job.return_value = failed_job
    mock_campaign_count.return_value = 2
    current_user = {"user_id": str(user_id)}
    db = AsyncMock()

    result = await get_client_detail(client.id, current_user, db)

    assert result.ingestion_failed is False
    assert result.brand_voice_profile == bvp
    assert result.campaign_count == 2


@patch("app.routers.clients.get_campaign_count")
@patch("app.routers.clients.get_latest_voice_job_for_client")
@patch("app.routers.clients.get_active_ingestion_job_for_client")
@patch("app.routers.clients.get_client")
async def test_get_client_detail_ingestion_failed_false_when_active_job_in_progress(
    mock_get_client, mock_active_job, mock_latest_job, mock_campaign_count
):
    """ingestion_failed=False when active job is present (AC #2 — in-progress state)."""
    from app.routers.clients import get_client_detail

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id, bvp=None)
    active_job = _make_job(status="in_progress")
    mock_get_client.return_value = client
    mock_active_job.return_value = active_job
    mock_latest_job.return_value = active_job
    mock_campaign_count.return_value = 0
    current_user = {"user_id": str(user_id)}
    db = AsyncMock()

    result = await get_client_detail(client.id, current_user, db)

    assert result.ingestion_failed is False
    assert result.job_id == active_job.id


@patch("app.routers.clients.get_campaign_count")
@patch("app.routers.clients.get_latest_voice_job_for_client")
@patch("app.routers.clients.get_active_ingestion_job_for_client")
@patch("app.routers.clients.get_client")
async def test_get_client_detail_ingestion_failed_false_when_no_prior_jobs(
    mock_get_client, mock_active_job, mock_latest_job, mock_campaign_count
):
    """ingestion_failed=False when no jobs exist — fresh client, questionnaire shown (AC #5)."""
    from app.routers.clients import get_client_detail

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id, bvp=None)
    mock_get_client.return_value = client
    mock_active_job.return_value = None
    mock_latest_job.return_value = None
    mock_campaign_count.return_value = 0
    current_user = {"user_id": str(user_id)}
    db = AsyncMock()

    result = await get_client_detail(client.id, current_user, db)

    assert result.ingestion_failed is False
    assert result.job_id is None
    assert result.ingestion_error is None


# ═══════════════════════════════════════════════════════════════════════════════
# PATCH /clients/{client_id} with brand_voice_profile  (AC #3, Task 8)
# ═══════════════════════════════════════════════════════════════════════════════

@patch("app.routers.clients.get_campaign_count")
@patch("app.routers.clients.get_active_ingestion_job_for_client")
@patch("app.routers.clients.update_client")
@patch("app.routers.clients.get_client")
async def test_patch_client_bvp_saves_profile_without_reingestion(
    mock_get_client, mock_update, mock_active_job, mock_campaign_count
):
    """PATCH with brand_voice_profile saves it and does NOT trigger re-ingestion (AC #3, Task 8)."""
    from app.routers.clients import update_client_detail

    user_id = uuid.uuid4()
    bvp = {
        "tone": ["authoritative", "direct"],
        "cadence": {"avg_sentence_length": 18, "variation_pattern": "punchy", "paragraph_structure": "3-5"},
        "banned_jargon": ["leverage", "synergy"],
    }
    client = _make_client(user_id=user_id)
    updated = _make_client(user_id=user_id)
    updated.id = client.id
    updated.brand_voice_profile = bvp
    mock_get_client.return_value = client
    mock_update.return_value = updated
    mock_active_job.return_value = None
    mock_campaign_count.return_value = 0
    current_user = {"user_id": str(user_id)}
    db = AsyncMock()
    bg = MagicMock()

    result = await update_client_detail(
        client.id, ClientUpdate(brand_voice_profile=bvp), bg, current_user, db
    )

    assert result.brand_voice_profile == bvp
    # No ingest worker dispatched — BVP update is a direct overwrite (Task 8)
    bg.add_task.assert_not_called()
    mock_update.assert_called_once_with(db, client.id, brand_voice_profile=bvp)


@patch("app.routers.clients.get_campaign_count")
@patch("app.routers.clients.get_active_ingestion_job_for_client")
@patch("app.routers.clients.update_client")
@patch("app.routers.clients.get_client")
async def test_patch_client_bvp_update_commits_to_db(
    mock_get_client, mock_update, mock_active_job, mock_campaign_count
):
    """BVP PATCH calls db.commit() once — the update is persisted."""
    from app.routers.clients import update_client_detail

    user_id = uuid.uuid4()
    bvp = {"tone": ["friendly"], "cadence": {}, "banned_jargon": []}
    client = _make_client(user_id=user_id)
    updated = _make_client(user_id=user_id)
    updated.id = client.id
    updated.brand_voice_profile = bvp
    mock_get_client.return_value = client
    mock_update.return_value = updated
    mock_active_job.return_value = None
    mock_campaign_count.return_value = 0
    current_user = {"user_id": str(user_id)}
    db = AsyncMock()
    bg = MagicMock()

    await update_client_detail(
        client.id, ClientUpdate(brand_voice_profile=bvp), bg, current_user, db
    )

    db.commit.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════════
# QuestionnaireRequest schema  (AC #6)
# ═══════════════════════════════════════════════════════════════════════════════

def test_questionnaire_request_defaults_empty_lists():
    """sample_texts and reference_urls default to [] when not provided."""
    req = QuestionnaireRequest(
        tone_sliders={"formal_casual": 3, "professional_friendly": 3, "concise_elaborate": 3}
    )
    assert req.sample_texts == []
    assert req.reference_urls == []


def test_questionnaire_request_accepts_full_payload():
    """Full questionnaire payload is valid."""
    req = QuestionnaireRequest(
        tone_sliders={"formal_casual": 2, "professional_friendly": 4, "concise_elaborate": 3},
        sample_texts=["Sample 1", "Sample 2"],
        reference_urls=["https://paulgraham.com"],
    )
    assert req.tone_sliders.formal_casual == 2
    assert req.tone_sliders.professional_friendly == 4
    assert len(req.sample_texts) == 2
    assert len(req.reference_urls) == 1
