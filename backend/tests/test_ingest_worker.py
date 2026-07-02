"""Unit tests for workers/ingest.py."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest


def _make_job(job_id=None, status="pending"):
    j = MagicMock()
    j.id = job_id or uuid.uuid4()
    j.status = status
    j.started_at = None
    j.completed_at = None
    j.error_details = None
    return j


def _make_client(client_id=None, website_url="https://example.com"):
    c = MagicMock()
    c.id = client_id or uuid.uuid4()
    c.website_url = website_url
    c.brand_voice_profile = None
    return c


def _db_sequence(*values):
    """Returns an AsyncMock whose .execute() returns sequential scalar_one_or_none results."""
    db = AsyncMock()
    results = []
    for v in values:
        r = MagicMock()
        r.scalar_one_or_none.return_value = v
        results.append(r)
    db.execute = AsyncMock(side_effect=results)
    return db


# ── ingest_worker: job not found ──────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.workers.ingest.AsyncSessionLocal")
async def test_ingest_worker_job_not_found_returns_early(mock_session_cls):
    from app.workers.ingest import ingest_worker

    db = _db_sequence(None)  # job lookup returns None
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_session_cls.return_value = ctx

    # Should not raise
    await ingest_worker(uuid.uuid4(), uuid.uuid4())

    # commit was never called (early return)
    db.commit.assert_not_called()


# ── ingest_worker: client not found ──────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.workers.ingest.AsyncSessionLocal")
async def test_ingest_worker_client_not_found_marks_failed(mock_session_cls):
    from app.workers.ingest import ingest_worker

    job = _make_job()
    db = _db_sequence(job, None)  # job found, client not found
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_session_cls.return_value = ctx

    await ingest_worker(job.id, uuid.uuid4())

    assert job.status == "failed"
    assert "not found" in (job.error_details or "").lower()


# ── ingest_worker: scraping fails but files succeed ───────────────────────────

@pytest.mark.asyncio
@patch("app.workers.ingest.extract_voice_profile", new_callable=AsyncMock)
@patch("app.workers.ingest.supabase_storage.download_file", new_callable=AsyncMock)
@patch("app.workers.ingest.supabase_storage.list_files", new_callable=AsyncMock)
@patch("app.workers.ingest.scrape_website", new_callable=AsyncMock)
@patch("app.workers.ingest.AsyncSessionLocal")
async def test_ingest_worker_scraping_failure_continues_with_files(
    mock_session_cls,
    mock_scrape,
    mock_list_files,
    mock_download,
    mock_voice,
):
    from app.workers.ingest import ingest_worker
    from app.services.ingestion import ScrapingError

    job_id = uuid.uuid4()
    client_id = uuid.uuid4()
    job = _make_job(job_id=job_id)
    client = _make_client(client_id=client_id, website_url="https://example.com")

    db = _db_sequence(job, client)
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_session_cls.return_value = ctx

    mock_scrape.side_effect = ScrapingError("site down")
    mock_list_files.return_value = [{"name": "post.txt"}]
    mock_download.return_value = b"Brand voice content from file"
    mock_voice.return_value = {"tone": "professional"}

    await ingest_worker(job_id, client_id)

    # Job should complete (not fail) because file text was available
    assert job.status == "complete"
    mock_voice.assert_called_once()


# ── ingest_worker: no text at all → fails ────────────────────────────────────

@pytest.mark.asyncio
@patch("app.workers.ingest.supabase_storage.list_files", new_callable=AsyncMock)
@patch("app.workers.ingest.scrape_website", new_callable=AsyncMock)
@patch("app.workers.ingest.AsyncSessionLocal")
async def test_ingest_worker_no_text_marks_failed(
    mock_session_cls,
    mock_scrape,
    mock_list_files,
):
    from app.workers.ingest import ingest_worker
    from app.services.ingestion import ScrapingError

    job_id = uuid.uuid4()
    client_id = uuid.uuid4()
    job = _make_job(job_id=job_id)
    client = _make_client(client_id=client_id, website_url="https://example.com")

    db = _db_sequence(job, client)
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_session_cls.return_value = ctx

    mock_scrape.side_effect = ScrapingError("site down")
    mock_list_files.return_value = []  # No files either

    await ingest_worker(job_id, client_id)

    assert job.status == "failed"
    assert job.error_details is not None


# ── ingest_worker: success path ───────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.workers.ingest.extract_voice_profile", new_callable=AsyncMock)
@patch("app.workers.ingest.supabase_storage.list_files", new_callable=AsyncMock)
@patch("app.workers.ingest.scrape_website", new_callable=AsyncMock)
@patch("app.workers.ingest.AsyncSessionLocal")
async def test_ingest_worker_success_sets_completed(
    mock_session_cls,
    mock_scrape,
    mock_list_files,
    mock_voice,
):
    from app.workers.ingest import ingest_worker

    job_id = uuid.uuid4()
    client_id = uuid.uuid4()
    job = _make_job(job_id=job_id)
    client = _make_client(client_id=client_id)

    db = _db_sequence(job, client)
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_session_cls.return_value = ctx

    mock_scrape.return_value = "Scraped content about the brand."
    mock_list_files.return_value = []
    mock_voice.return_value = {"tone": "conversational"}

    await ingest_worker(job_id, client_id)

    assert job.status == "complete"
    assert job.completed_at is not None
    assert client.brand_voice_profile == {"tone": "conversational"}


# ── ingest_worker: client without website_url skips scrape ───────────────────

@pytest.mark.asyncio
@patch("app.workers.ingest.extract_voice_profile", new_callable=AsyncMock)
@patch("app.workers.ingest.supabase_storage.list_files", new_callable=AsyncMock)
@patch("app.workers.ingest.scrape_website", new_callable=AsyncMock)
@patch("app.workers.ingest.AsyncSessionLocal")
async def test_ingest_worker_voice_extraction_failure_marks_failed(
    mock_session_cls,
    mock_scrape,
    mock_list_files,
    mock_voice,
):
    from app.workers.ingest import ingest_worker

    job_id = uuid.uuid4()
    client_id = uuid.uuid4()
    job = _make_job(job_id=job_id)
    client = _make_client(client_id=client_id)

    db = _db_sequence(job, client)
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_session_cls.return_value = ctx

    mock_scrape.return_value = "Good scraped content."
    mock_list_files.return_value = []
    mock_voice.side_effect = RuntimeError("Gemini API error")

    await ingest_worker(job_id, client_id)

    assert job.status == "failed"
    assert "Voice extraction failed" in (job.error_details or "")


@pytest.mark.asyncio
@patch("app.workers.ingest.extract_voice_profile", new_callable=AsyncMock)
@patch("app.workers.ingest.supabase_storage.download_file", new_callable=AsyncMock)
@patch("app.workers.ingest.supabase_storage.list_files", new_callable=AsyncMock)
@patch("app.workers.ingest.scrape_website", new_callable=AsyncMock)
@patch("app.workers.ingest.AsyncSessionLocal")
async def test_ingest_worker_single_file_download_failure_continues(
    mock_session_cls,
    mock_scrape,
    mock_list_files,
    mock_download,
    mock_voice,
):
    """If one file fails to download, the worker skips it and continues with others."""
    from app.workers.ingest import ingest_worker

    job_id = uuid.uuid4()
    client_id = uuid.uuid4()
    job = _make_job(job_id=job_id)
    client = _make_client(client_id=client_id, website_url=None)

    db = _db_sequence(job, client)
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_session_cls.return_value = ctx

    mock_scrape.return_value = ""  # no website
    mock_list_files.return_value = [{"name": "fail.txt"}, {"name": "good.txt"}]

    def download_side_effect(bucket, path):
        if "fail.txt" in path:
            raise Exception("Download failed for this file")
        return b"Good file content"

    mock_download.side_effect = download_side_effect
    mock_voice.return_value = {"tone": "friendly"}

    await ingest_worker(job_id, client_id)

    # Job should complete using only the good file's text
    assert job.status == "complete"
    mock_voice.assert_called_once()


@pytest.mark.asyncio
@patch("app.workers.ingest.extract_voice_profile", new_callable=AsyncMock)
@patch("app.workers.ingest.supabase_storage.list_files", new_callable=AsyncMock)
@patch("app.workers.ingest.scrape_website", new_callable=AsyncMock)
@patch("app.workers.ingest.AsyncSessionLocal")
async def test_ingest_worker_sets_in_progress_status(
    mock_session_cls,
    mock_scrape,
    mock_list_files,
    mock_voice,
):
    """Worker sets job.status='in_progress' and job.started_at before processing."""
    from app.workers.ingest import ingest_worker

    job_id = uuid.uuid4()
    client_id = uuid.uuid4()
    job = _make_job(job_id=job_id)
    client = _make_client(client_id=client_id)

    status_at_commit: list[str] = []

    db = _db_sequence(job, client)
    original_commit = db.commit

    async def track_commit():
        status_at_commit.append(job.status)
        await original_commit()

    db.commit = track_commit
    db.refresh = AsyncMock()

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_session_cls.return_value = ctx

    mock_scrape.return_value = "Some text."
    mock_list_files.return_value = []
    mock_voice.return_value = {}

    await ingest_worker(job_id, client_id)

    # First commit should have status='in_progress'
    assert "in_progress" in status_at_commit
    # started_at should have been set
    assert job.started_at is not None


# ── ingest_worker: no url skips scraping ─────────────────────────────────────

@pytest.mark.asyncio
@patch("app.workers.ingest.extract_voice_profile", new_callable=AsyncMock)
@patch("app.workers.ingest.supabase_storage.download_file", new_callable=AsyncMock)
@patch("app.workers.ingest.supabase_storage.list_files", new_callable=AsyncMock)
@patch("app.workers.ingest.scrape_website", new_callable=AsyncMock)
@patch("app.workers.ingest.AsyncSessionLocal")
async def test_ingest_worker_no_url_skips_scraping(
    mock_session_cls,
    mock_scrape,
    mock_list_files,
    mock_download,
    mock_voice,
):
    from app.workers.ingest import ingest_worker

    job_id = uuid.uuid4()
    client_id = uuid.uuid4()
    job = _make_job(job_id=job_id)
    client = _make_client(client_id=client_id, website_url=None)

    db = _db_sequence(job, client)
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_session_cls.return_value = ctx

    mock_list_files.return_value = [{"name": "guide.txt"}]
    mock_download.return_value = b"Content from uploaded file."
    mock_voice.return_value = {}

    await ingest_worker(job_id, client_id)

    # scrape_website should NOT have been called
    mock_scrape.assert_not_called()
    # job still completes via file text
    assert job.status == "complete"
