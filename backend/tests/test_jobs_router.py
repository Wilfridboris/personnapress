"""Unit tests for routers/jobs.py — GET /api/v1/jobs/{job_id}."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_job(job_id=None, client_id=None, status="completed"):
    j = MagicMock()
    j.id = job_id or uuid.uuid4()
    j.client_id = client_id
    j.campaign_id = None
    j.job_type = "ingest"
    j.status = status
    j.scheduled_at = None
    j.started_at = datetime(2026, 7, 1, 10, 0, 0, tzinfo=timezone.utc)
    j.completed_at = datetime(2026, 7, 1, 10, 1, 0, tzinfo=timezone.utc)
    j.attempt_count = 1
    j.error_details = None
    j.created_at = datetime(2026, 7, 1, 9, 59, 0, tzinfo=timezone.utc)
    return j


def _make_client(user_id=None):
    c = MagicMock()
    c.id = uuid.uuid4()
    c.user_id = user_id or uuid.uuid4()
    return c


def _db_sequence(*values):
    db = AsyncMock()
    results = []
    for v in values:
        r = MagicMock()
        r.scalar_one_or_none.return_value = v
        results.append(r)
    db.execute = AsyncMock(side_effect=results)
    return db


# ── get_job: happy path ───────────────────────────────────────────────────────

async def test_get_job_happy_path_returns_job_response():
    from app.routers.jobs import get_job

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    job = _make_job(client_id=client.id)
    db = _db_sequence(job, client)

    result = await get_job(
        job_id=job.id,
        current_user={"user_id": str(user_id)},
        db=db,
    )

    assert result.id == job.id
    assert result.status == "completed"
    assert result.job_type == "ingest"
    assert result.started_at == job.started_at
    assert result.completed_at == job.completed_at
    assert result.error_details is None


# ── get_job: 401 when session invalid ────────────────────────────────────────

async def test_get_job_raises_401_on_bad_session():
    from app.routers.jobs import get_job

    with pytest.raises(HTTPException) as exc_info:
        await get_job(
            job_id=uuid.uuid4(),
            current_user={},  # no user_id key
            db=AsyncMock(),
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["error"]["code"] == "INVALID_SESSION"


async def test_get_job_raises_401_on_invalid_uuid_in_session():
    from app.routers.jobs import get_job

    with pytest.raises(HTTPException) as exc_info:
        await get_job(
            job_id=uuid.uuid4(),
            current_user={"user_id": "not-a-uuid"},
            db=AsyncMock(),
        )

    assert exc_info.value.status_code == 401


# ── get_job: 404 when job not found ──────────────────────────────────────────

async def test_get_job_raises_404_when_job_not_found():
    from app.routers.jobs import get_job

    db = _db_sequence(None)  # job lookup returns None

    with pytest.raises(HTTPException) as exc_info:
        await get_job(
            job_id=uuid.uuid4(),
            current_user={"user_id": str(uuid.uuid4())},
            db=db,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["error"]["code"] == "JOB_NOT_FOUND"


# ── get_job: 404 when job's client belongs to another user ───────────────────

async def test_get_job_raises_404_when_client_belongs_to_other_user():
    from app.routers.jobs import get_job

    owner_id = uuid.uuid4()
    requester_id = uuid.uuid4()
    client = _make_client(user_id=owner_id)
    job = _make_job(client_id=client.id)

    db = _db_sequence(job, client)

    with pytest.raises(HTTPException) as exc_info:
        await get_job(
            job_id=job.id,
            current_user={"user_id": str(requester_id)},
            db=db,
        )

    assert exc_info.value.status_code == 404  # returns 404, not 403, to avoid info leak


# ── get_job: job with no client_id and no campaign_id (orphaned job) ─────────

async def test_get_job_with_no_client_id_and_no_campaign_id_returns_200():
    """Jobs with neither client_id nor campaign_id are accessible by any authenticated user."""
    from app.routers.jobs import get_job

    job = _make_job(client_id=None)  # no client linked
    job.campaign_id = None           # no campaign linked either
    db = _db_sequence(job)           # only one DB lookup (no ownership check)

    result = await get_job(
        job_id=job.id,
        current_user={"user_id": str(uuid.uuid4())},
        db=db,
    )

    assert result.id == job.id
    assert result.client_id is None


async def test_get_job_campaign_level_job_returns_200_for_owner():
    """Campaign-level jobs are accessible only by the owning user (via campaign → client chain)."""
    from app.routers.jobs import get_job
    import uuid as _uuid

    user_id = _uuid.uuid4()
    client_id = _uuid.uuid4()
    campaign_id = _uuid.uuid4()

    job = _make_job(client_id=None)
    job.campaign_id = campaign_id

    campaign = MagicMock()
    campaign.id = campaign_id
    campaign.client_id = client_id

    client = _make_client(user_id=user_id)
    client.id = client_id

    db = _db_sequence(job, campaign, client)

    result = await get_job(
        job_id=job.id,
        current_user={"user_id": str(user_id)},
        db=db,
    )

    assert result.id == job.id


async def test_get_job_campaign_level_job_raises_404_for_non_owner():
    """Campaign-level jobs are NOT accessible by users who do not own the campaign's client."""
    from app.routers.jobs import get_job
    from fastapi import HTTPException as _HTTPException
    import uuid as _uuid

    owner_id = _uuid.uuid4()
    requester_id = _uuid.uuid4()
    client_id = _uuid.uuid4()
    campaign_id = _uuid.uuid4()

    job = _make_job(client_id=None)
    job.campaign_id = campaign_id

    campaign = MagicMock()
    campaign.id = campaign_id
    campaign.client_id = client_id

    client = _make_client(user_id=owner_id)
    client.id = client_id

    db = _db_sequence(job, campaign, client)

    with pytest.raises(_HTTPException) as exc_info:
        await get_job(
            job_id=job.id,
            current_user={"user_id": str(requester_id)},
            db=db,
        )

    assert exc_info.value.status_code == 404


# ── get_job: 404 when client record missing (orphaned job) ───────────────────

async def test_get_job_raises_404_when_client_record_missing():
    from app.routers.jobs import get_job

    job = _make_job(client_id=uuid.uuid4())
    db = _db_sequence(job, None)  # job found, client lookup returns None

    with pytest.raises(HTTPException) as exc_info:
        await get_job(
            job_id=job.id,
            current_user={"user_id": str(uuid.uuid4())},
            db=db,
        )

    assert exc_info.value.status_code == 404


# ── get_job: failed job exposes error_details ─────────────────────────────────

async def test_get_job_failed_job_includes_error_details():
    from app.routers.jobs import get_job

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    job = _make_job(client_id=client.id, status="failed")
    job.error_details = "Couldn't reach https://example.com: HTTP 403"
    db = _db_sequence(job, client)

    result = await get_job(
        job_id=job.id,
        current_user={"user_id": str(user_id)},
        db=db,
    )

    assert result.status == "failed"
    assert "HTTP 403" in result.error_details


# ── get_job: in_progress job status ──────────────────────────────────────────

async def test_get_job_in_progress_returns_status():
    from app.routers.jobs import get_job

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    job = _make_job(client_id=client.id, status="in_progress")
    job.completed_at = None
    db = _db_sequence(job, client)

    result = await get_job(
        job_id=job.id,
        current_user={"user_id": str(user_id)},
        db=db,
    )

    assert result.status == "in_progress"
    assert result.completed_at is None
