"""Unit tests for POST /clients/{id}/ingest (Story 2.6 — voice profile refresh)."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.routers.clients import trigger_voice_ingest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_client(user_id: uuid.UUID | None = None, with_url: bool = True):
    c = MagicMock()
    c.id = uuid.uuid4()
    c.user_id = user_id or uuid.uuid4()
    c.name = "Acme"
    c.website_url = "https://example.com" if with_url else None
    c.brand_voice_profile = {"tone": ["bold"]}
    c.created_at = "2026-01-01T00:00:00Z"
    return c


def _make_job():
    j = MagicMock()
    j.id = uuid.uuid4()
    j.status = "pending"
    return j


# ── Auth failures ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ingest_rejects_invalid_session():
    db = AsyncMock()
    bg = MagicMock()
    with pytest.raises(HTTPException) as exc_info:
        await trigger_voice_ingest(
            client_id=uuid.uuid4(),
            background_tasks=bg,
            current_user={"user_id": "not-a-uuid"},
            db=db,
        )
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_ingest_returns_404_when_client_not_found():
    db = AsyncMock()
    bg = MagicMock()
    with patch("app.routers.clients.get_client", new=AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as exc_info:
            await trigger_voice_ingest(
                client_id=uuid.uuid4(),
                background_tasks=bg,
                current_user={"user_id": str(uuid.uuid4())},
                db=db,
            )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_ingest_returns_403_when_wrong_owner():
    db = AsyncMock()
    bg = MagicMock()
    client = _make_client()  # different user_id
    caller_uid = uuid.uuid4()
    with patch("app.routers.clients.get_client", new=AsyncMock(return_value=client)):
        with pytest.raises(HTTPException) as exc_info:
            await trigger_voice_ingest(
                client_id=client.id,
                background_tasks=bg,
                current_user={"user_id": str(caller_uid)},
                db=db,
            )
    assert exc_info.value.status_code == 403


# ── Happy path ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ingest_nulls_bvp_creates_job_dispatches_worker():
    """AC#3: BVP is nulled, job created, worker dispatched, 202 + job_id returned."""
    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id, with_url=True)
    job = _make_job()
    bg = MagicMock()

    with (
        patch("app.routers.clients.get_client", new=AsyncMock(return_value=client)),
        patch("app.routers.clients.get_active_ingestion_job_for_client", new=AsyncMock(return_value=None)),
        patch("app.routers.clients.update_client", new=AsyncMock(return_value=client)) as mock_update,
        patch("app.routers.clients.create_job", new=AsyncMock(return_value=job)) as mock_create_job,
        patch("app.routers.clients.ingest_worker") as mock_worker,
    ):
        db = AsyncMock()
        result = await trigger_voice_ingest(
            client_id=client.id,
            background_tasks=bg,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    # BVP nulled
    mock_update.assert_awaited_once_with(db, client.id, brand_voice_profile=None)
    # Job created with correct type
    mock_create_job.assert_awaited_once()
    call_kwargs = mock_create_job.call_args
    assert call_kwargs.kwargs["job_type"] == "ingestion"
    assert call_kwargs.kwargs["status"] == "pending"
    # Worker dispatched
    bg.add_task.assert_called_once_with(mock_worker, job_id=job.id, client_id=client.id)
    # Returns job_id
    assert result == {"job_id": str(job.id)}


@pytest.mark.asyncio
async def test_ingest_dispatches_worker_even_without_url():
    """AC#5: no URL → worker still dispatched (worker detects no_content and marks failed)."""
    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id, with_url=False)
    job = _make_job()
    bg = MagicMock()

    with (
        patch("app.routers.clients.get_client", new=AsyncMock(return_value=client)),
        patch("app.routers.clients.get_active_ingestion_job_for_client", new=AsyncMock(return_value=None)),
        patch("app.routers.clients.update_client", new=AsyncMock(return_value=client)),
        patch("app.routers.clients.create_job", new=AsyncMock(return_value=job)),
        patch("app.routers.clients.ingest_worker") as mock_worker,
    ):
        db = AsyncMock()
        result = await trigger_voice_ingest(
            client_id=client.id,
            background_tasks=bg,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    bg.add_task.assert_called_once_with(mock_worker, job_id=job.id, client_id=client.id)
    assert "job_id" in result


@pytest.mark.asyncio
async def test_ingest_commits_before_background_task():
    """NFR-7: job record must be persisted (db.commit) before BackgroundTask dispatched."""
    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    job = _make_job()
    call_order: list[str] = []

    bg = MagicMock()

    original_add_task = bg.add_task
    def track_add_task(*args, **kwargs):
        call_order.append("bg.add_task")
        return original_add_task(*args, **kwargs)
    bg.add_task = track_add_task

    db = AsyncMock()
    original_commit = db.commit
    async def track_commit():
        call_order.append("db.commit")
        return await original_commit()
    db.commit = track_commit

    with (
        patch("app.routers.clients.get_client", new=AsyncMock(return_value=client)),
        patch("app.routers.clients.get_active_ingestion_job_for_client", new=AsyncMock(return_value=None)),
        patch("app.routers.clients.update_client", new=AsyncMock(return_value=client)),
        patch("app.routers.clients.create_job", new=AsyncMock(return_value=job)),
        patch("app.routers.clients.ingest_worker"),
    ):
        await trigger_voice_ingest(
            client_id=client.id,
            background_tasks=bg,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert call_order.index("db.commit") < call_order.index("bg.add_task")


# ── Active-job guard (P2) ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ingest_returns_existing_job_if_active():
    """P2: if an active ingestion job exists, return it without creating a new one."""
    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    existing_job = _make_job()
    bg = MagicMock()

    with (
        patch("app.routers.clients.get_client", new=AsyncMock(return_value=client)),
        patch(
            "app.routers.clients.get_active_ingestion_job_for_client",
            new=AsyncMock(return_value=existing_job),
        ),
        patch("app.routers.clients.update_client", new=AsyncMock()) as mock_update,
        patch("app.routers.clients.create_job", new=AsyncMock()) as mock_create,
    ):
        db = AsyncMock()
        result = await trigger_voice_ingest(
            client_id=client.id,
            background_tasks=bg,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result == {"job_id": str(existing_job.id)}
    mock_update.assert_not_awaited()
    mock_create.assert_not_awaited()
    bg.add_task.assert_not_called()


# ── update_client None guard (P3) ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ingest_returns_404_when_update_client_returns_none():
    """P3: if update_client returns None (client deleted between auth and write), raise 404."""
    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    bg = MagicMock()

    with (
        patch("app.routers.clients.get_client", new=AsyncMock(return_value=client)),
        patch(
            "app.routers.clients.get_active_ingestion_job_for_client",
            new=AsyncMock(return_value=None),
        ),
        patch("app.routers.clients.update_client", new=AsyncMock(return_value=None)),
    ):
        db = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await trigger_voice_ingest(
                client_id=client.id,
                background_tasks=bg,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 404
