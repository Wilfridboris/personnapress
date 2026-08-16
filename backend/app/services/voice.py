"""Voice transcription service.

Validates MIME type, creates a transcription job record, and returns the
job ID + audio bytes so the router can dispatch a BackgroundTask.
"""

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.jobs import create_job

_SUPPORTED_MIME_TYPES = {
    "audio/webm",
    "audio/webm;codecs=opus",
    "audio/mp4",
    "audio/mpeg",
    "audio/wav",
}

_AUDIO_FORMAT_UNSUPPORTED = {
    "error": {
        "code": "AUDIO_FORMAT_UNSUPPORTED",
        "message": "Unsupported audio format. Accepted formats: webm, mp4, mpeg, wav.",
        "detail": {},
    }
}


async def create_transcription_job(
    db: AsyncSession,
    content: bytes,
    content_type: str,
    user_id: uuid.UUID,
) -> tuple[uuid.UUID, bytes, str]:
    """Validate MIME type, create a pending transcription job, return (job_id, content, mime_type).

    The job is stamped with user_id so GET /jobs/{job_id} can enforce ownership.
    Raises HTTPException 415 for unsupported MIME types before creating any job record.
    """
    mime_type = content_type.split(";")[0].strip()
    # Re-include codec suffix for webm;codecs=opus matching
    full_mime = content_type.strip()

    if full_mime not in _SUPPORTED_MIME_TYPES and mime_type not in _SUPPORTED_MIME_TYPES:
        raise HTTPException(status_code=415, detail=_AUDIO_FORMAT_UNSUPPORTED)

    effective_mime = full_mime if full_mime in _SUPPORTED_MIME_TYPES else mime_type

    job = await create_job(
        db,
        job_type="transcription",
        status="pending",
        campaign_id=None,
        client_id=None,
        user_id=user_id,
    )
    return job.id, content, effective_mime
