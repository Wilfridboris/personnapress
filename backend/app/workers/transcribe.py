"""Transcription worker.

Receives (job_id, audio_bytes, mime_type) from the router's BackgroundTask,
calls Groq Whisper, and writes the transcript to job.result.
Creates its own DB session (the request-scoped session is closed before
BackgroundTasks execute -- same pattern as workers/generate.py).
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

import httpx
import sentry_sdk

from app.db.connection import AsyncSessionLocal
from app.db.repositories.jobs import get_job
from app.integrations import groq_audio

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 3
# Groq 429 (rate limit) and 5xx (server) errors are transient. 4xx client errors
# (bad key, unsupported format) and response-parse errors are not worth retrying.
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _is_retryable(exc: Exception) -> bool:
    """Return True only for transient Groq failures (429/5xx) and network errors."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _RETRYABLE_STATUS
    return isinstance(exc, httpx.RequestError)


async def run_transcription(job_id: uuid.UUID, audio_bytes: bytes, mime_type: str) -> None:
    """BackgroundTask entry point: transcribe audio and persist the result."""
    try:
        async with AsyncSessionLocal() as db:
            job = await get_job(db, job_id)
            if not job or job.status != "pending":
                logger.warning(
                    "run_transcription: job %s skipped (status=%s)",
                    job_id,
                    job.status if job else "not found",
                )
                return

            job.status = "in_progress"
            job.started_at = _utcnow()
            await db.commit()

            transcript: str | None = None
            last_error: Exception | None = None
            attempts = 0

            try:
                for attempt in range(_MAX_ATTEMPTS):
                    attempts = attempt + 1
                    try:
                        transcript = await groq_audio.transcribe(audio_bytes, mime_type)
                        break
                    except Exception as exc:
                        last_error = exc
                        retryable = _is_retryable(exc)
                        logger.warning(
                            "run_transcription: attempt %d/%d failed for job %s (retryable=%s): %s",
                            attempts,
                            _MAX_ATTEMPTS,
                            job_id,
                            retryable,
                            exc,
                        )
                        if not retryable:
                            break
                        if attempt < _MAX_ATTEMPTS - 1:
                            await asyncio.sleep(2 ** attempt)
            finally:
                # Release the audio bytes once transcription is done, whatever the
                # outcome. They are never written to disk, storage, or any DB column.
                audio_bytes = b""

            job = await get_job(db, job_id)
            if not job:
                logger.error("run_transcription: job %s disappeared after transcription", job_id)
                return

            job.attempt_count = attempts
            if transcript is not None:
                job.result = {"transcript": transcript}
                job.status = "complete"
                job.completed_at = _utcnow()
            else:
                # Log the raw failure for operators; return a safe message to the client.
                logger.error(
                    "run_transcription: job %s failed after %d attempt(s)",
                    job_id,
                    attempts,
                    exc_info=last_error,
                )
                job.error_details = "Transcription failed. Please try recording again."
                job.status = "failed"
                job.completed_at = _utcnow()

            await db.commit()

    except Exception as exc:
        logger.exception("run_transcription: unhandled error for job %s", job_id)
        sentry_sdk.capture_exception(exc)
