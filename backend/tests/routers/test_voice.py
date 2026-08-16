"""Unit tests for routers/voice.py — POST /api/v1/voice/transcribe."""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.testclient import TestClient


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_upload_file(content: bytes = b"audio data", content_type: str = "audio/webm") -> MagicMock:
    uf = MagicMock()
    uf.read = AsyncMock(return_value=content)
    uf.content_type = content_type
    return uf


def _make_starlette_request(content_length: str | None = None) -> Request:
    """Build a minimal real starlette Request (needed by slowapi decorator)."""
    headers = [(b"content-type", b"multipart/form-data")]
    if content_length is not None:
        headers.append((b"content-length", content_length.encode()))
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/voice/transcribe",
        "query_string": b"",
        "headers": headers,
        "app": MagicMock(state=MagicMock(limiter=MagicMock())),
    }
    return Request(scope)


def _make_background_tasks() -> MagicMock:
    bt = MagicMock()
    bt.add_task = MagicMock()
    return bt


# ── AC 7: 413 when Content-Length exceeds 10 MB ──────────────────────────────

async def test_transcribe_audio_raises_413_on_large_content_length():
    from app.routers.voice import transcribe_audio

    request = _make_starlette_request(content_length=str(10_485_761))
    file = _make_upload_file()

    with pytest.raises(HTTPException) as exc_info:
        await transcribe_audio(
            request=request,
            file=file,
            background_tasks=_make_background_tasks(),
            current_user={"user_id": str(uuid.uuid4())},
            db=AsyncMock(),
        )

    assert exc_info.value.status_code == 413
    assert exc_info.value.detail["error"]["code"] == "AUDIO_TOO_LARGE"


# ── AC 7: 413 when actual body exceeds 10 MB (client lied about Content-Length) ──

async def test_transcribe_audio_raises_413_on_large_actual_body():
    from app.routers.voice import transcribe_audio

    big_content = b"x" * 10_485_761
    request = _make_starlette_request(content_length=None)
    file = _make_upload_file(content=big_content)

    with pytest.raises(HTTPException) as exc_info:
        await transcribe_audio(
            request=request,
            file=file,
            background_tasks=_make_background_tasks(),
            current_user={"user_id": str(uuid.uuid4())},
            db=AsyncMock(),
        )

    assert exc_info.value.status_code == 413
    assert exc_info.value.detail["error"]["code"] == "AUDIO_TOO_LARGE"


# ── AC 7: 202 on valid upload — background task dispatched ───────────────────

async def test_transcribe_audio_returns_202_with_job_id():
    from app.routers.voice import transcribe_audio

    job_id = uuid.uuid4()
    request = _make_starlette_request(content_length="1024")
    file = _make_upload_file(content=b"valid audio", content_type="audio/webm")
    background_tasks = _make_background_tasks()
    db = AsyncMock()

    with patch("app.routers.voice.create_transcription_job", new=AsyncMock(return_value=(job_id, b"valid audio", "audio/webm"))):
        with patch("app.routers.voice.run_transcription"):
            response = await transcribe_audio(
                request=request,
                file=file,
                background_tasks=background_tasks,
                current_user={"user_id": str(uuid.uuid4())},
                db=db,
            )

    assert response.status_code == 202
    body = json.loads(response.body)
    assert body["job_id"] == str(job_id)
    background_tasks.add_task.assert_called_once()


# ── Empty audio upload is rejected with 422 before any job is created ─────────

async def test_transcribe_audio_raises_422_on_empty_audio():
    from app.routers.voice import transcribe_audio

    request = _make_starlette_request(content_length="0")
    file = _make_upload_file(content=b"")

    with patch("app.routers.voice.create_transcription_job") as mock_create:
        with pytest.raises(HTTPException) as exc_info:
            await transcribe_audio(
                request=request,
                file=file,
                background_tasks=_make_background_tasks(),
                current_user={"user_id": str(uuid.uuid4())},
                db=AsyncMock(),
            )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["error"]["code"] == "AUDIO_EMPTY"
    mock_create.assert_not_called()


# ── AC 5: 415 for unsupported MIME type ──────────────────────────────────────

async def test_create_transcription_job_raises_415_for_unsupported_mime():
    from app.services.voice import create_transcription_job

    db = AsyncMock()
    with pytest.raises(HTTPException) as exc_info:
        await create_transcription_job(db, b"audio data", "video/mp4", uuid.uuid4())

    assert exc_info.value.status_code == 415
    assert exc_info.value.detail["error"]["code"] == "AUDIO_FORMAT_UNSUPPORTED"


# ── AC 5: no job record created on 415 ───────────────────────────────────────

async def test_create_transcription_job_no_job_created_on_bad_mime():
    from app.services.voice import create_transcription_job

    db = AsyncMock()
    with patch("app.services.voice.create_job") as mock_create:
        with pytest.raises(HTTPException):
            await create_transcription_job(db, b"audio data", "application/octet-stream", uuid.uuid4())
    mock_create.assert_not_called()


# ── AC 5: supported MIME types create a job ──────────────────────────────────

@pytest.mark.parametrize("mime_type", [
    "audio/webm",
    "audio/webm;codecs=opus",
    "audio/mp4",
    "audio/mpeg",
    "audio/wav",
])
async def test_create_transcription_job_accepts_supported_mime_types(mime_type):
    from app.services.voice import create_transcription_job

    job_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_job = MagicMock()
    mock_job.id = job_id

    with patch("app.services.voice.create_job", new=AsyncMock(return_value=mock_job)) as mock_create:
        result_id, result_bytes, result_mime = await create_transcription_job(AsyncMock(), b"audio", mime_type, user_id)

    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args[1]
    assert call_kwargs["job_type"] == "transcription"
    assert call_kwargs["status"] == "pending"
    assert call_kwargs["campaign_id"] is None
    assert call_kwargs["client_id"] is None
    assert call_kwargs["user_id"] == user_id
    assert result_id == job_id
    assert result_bytes == b"audio"


# ── AC 6: worker success path writes result ──────────────────────────────────

async def test_run_transcription_writes_result_on_success():
    from app.workers.transcribe import run_transcription

    job_id = uuid.uuid4()
    mock_job = MagicMock()
    mock_job.id = job_id
    mock_job.status = "pending"

    db = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)
    db.commit = AsyncMock()

    with patch("app.workers.transcribe.AsyncSessionLocal", return_value=db):
        with patch("app.workers.transcribe.get_job", new=AsyncMock(return_value=mock_job)):
            with patch("app.workers.transcribe.groq_audio.transcribe", new=AsyncMock(return_value="Hello world")):
                await run_transcription(job_id=job_id, audio_bytes=b"audio", mime_type="audio/webm")

    assert mock_job.result == {"transcript": "Hello world"}
    assert mock_job.status == "complete"
    assert mock_job.completed_at is not None


# ── AC 6: retryable failure (5xx) retries the full 3 attempts, then fails ──────

async def test_run_transcription_retries_then_fails_on_retryable_error():
    import httpx
    from types import SimpleNamespace
    from app.workers.transcribe import run_transcription

    job_id = uuid.uuid4()
    job = SimpleNamespace(
        id=job_id, status="pending", result=None, error_details=None,
        attempt_count=0, started_at=None, completed_at=None,
    )

    db = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)
    db.commit = AsyncMock()

    retryable = httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock(status_code=500))
    groq = AsyncMock(side_effect=retryable)

    with patch("app.workers.transcribe.asyncio.sleep", new=AsyncMock()) as mock_sleep:
        with patch("app.workers.transcribe.AsyncSessionLocal", return_value=db):
            with patch("app.workers.transcribe.get_job", new=AsyncMock(return_value=job)):
                with patch("app.workers.transcribe.groq_audio.transcribe", new=groq):
                    await run_transcription(job_id=job_id, audio_bytes=b"audio", mime_type="audio/webm")

    assert job.status == "failed"
    assert job.result is None
    assert job.attempt_count == 3
    assert "Transcription failed" in job.error_details
    assert groq.await_count == 3
    # Backoff sleeps between the 3 attempts (not after the last one).
    assert mock_sleep.await_count == 2


# ── AC 6: non-retryable failure (4xx) fails fast without retrying ──────────────

async def test_run_transcription_does_not_retry_non_retryable_error():
    import httpx
    from types import SimpleNamespace
    from app.workers.transcribe import run_transcription

    job_id = uuid.uuid4()
    job = SimpleNamespace(
        id=job_id, status="pending", result=None, error_details=None,
        attempt_count=0, started_at=None, completed_at=None,
    )

    db = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)
    db.commit = AsyncMock()

    non_retryable = httpx.HTTPStatusError("401", request=MagicMock(), response=MagicMock(status_code=401))
    groq = AsyncMock(side_effect=non_retryable)

    with patch("app.workers.transcribe.asyncio.sleep", new=AsyncMock()):
        with patch("app.workers.transcribe.AsyncSessionLocal", return_value=db):
            with patch("app.workers.transcribe.get_job", new=AsyncMock(return_value=job)):
                with patch("app.workers.transcribe.groq_audio.transcribe", new=groq):
                    await run_transcription(job_id=job_id, audio_bytes=b"audio", mime_type="audio/webm")

    assert job.status == "failed"
    assert job.result is None
    assert job.attempt_count == 1
    assert groq.await_count == 1


# ── AC 4: groq_audio raises on non-2xx ───────────────────────────────────────

async def test_groq_audio_transcribe_raises_on_non_2xx():
    from app.integrations.groq_audio import transcribe
    import httpx

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500", request=MagicMock(), response=MagicMock()
    )

    with patch("app.integrations.groq_audio.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        with pytest.raises(httpx.HTTPStatusError):
            await transcribe(b"audio", "audio/webm")


# ── AC 4: groq_audio returns transcript text on success ──────────────────────

async def test_groq_audio_transcribe_returns_text():
    from app.integrations.groq_audio import transcribe

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"text": "Transcribed content here"}

    with patch("app.integrations.groq_audio.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await transcribe(b"audio bytes", "audio/mp4")

    assert result == "Transcribed content here"


# ── AC 2: JobResponse includes result field ───────────────────────────────────

def test_job_response_includes_result_field():
    from app.schemas.job import JobResponse
    import datetime

    response = JobResponse(
        id=uuid.uuid4(),
        job_type="transcription",
        status="complete",
        attempt_count=1,
        created_at=datetime.datetime.utcnow(),
        result={"transcript": "Hello from Groq"},
    )
    assert response.result == {"transcript": "Hello from Groq"}


def test_job_response_result_defaults_to_none():
    from app.schemas.job import JobResponse
    import datetime

    response = JobResponse(
        id=uuid.uuid4(),
        job_type="generation",
        status="complete",
        attempt_count=1,
        created_at=datetime.datetime.utcnow(),
    )
    assert response.result is None
