"""Voice transcription router.

POST /api/v1/voice/transcribe — accepts audio uploads, enforces size and rate
limits, creates a transcription job, and returns 202 with job_id.
The frontend polls GET /api/v1/jobs/{job_id} to retrieve the transcript.
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile
from jose import jwt
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.db.connection import get_session
from app.services.voice import create_transcription_job
from app.workers.transcribe import run_transcription

router = APIRouter(prefix="/voice", tags=["voice"])

_MAX_AUDIO_BYTES = 10_485_760  # 10 MB

_AUDIO_TOO_LARGE = {
    "error": {
        "code": "AUDIO_TOO_LARGE",
        "message": "Audio file exceeds the 10 MB limit.",
        "detail": {},
    }
}

_AUDIO_EMPTY = {
    "error": {
        "code": "AUDIO_EMPTY",
        "message": "Audio file is empty. Please record something before submitting.",
        "detail": {},
    }
}

_INVALID_SESSION = {"error": {"code": "INVALID_SESSION", "message": "Invalid session.", "detail": {}}}


def _voice_rate_key(request: Request) -> str:
    """Rate-limit by user_id from JWT cookie; fall back to IP."""
    try:
        token = request.cookies.get("session", "")
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("user_id", "")
        return str(user_id) if user_id else get_remote_address(request)
    except Exception:
        return get_remote_address(request)


@router.post("/transcribe")
@limiter.limit("5/hour", key_func=_voice_rate_key)
async def transcribe_audio(
    request: Request,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> JSONResponse:
    try:
        user_id = uuid.UUID(current_user["user_id"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail=_INVALID_SESSION)

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            declared_length = int(content_length)
        except ValueError:
            declared_length = None
        if declared_length is not None and declared_length > _MAX_AUDIO_BYTES:
            raise HTTPException(status_code=413, detail=_AUDIO_TOO_LARGE)

    content = await file.read()
    if len(content) > _MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail=_AUDIO_TOO_LARGE)
    if not content:
        raise HTTPException(status_code=422, detail=_AUDIO_EMPTY)

    mime_type = file.content_type or "audio/webm"
    job_id, audio_bytes, effective_mime = await create_transcription_job(db, content, mime_type, user_id)

    # Commit job record BEFORE dispatching BackgroundTask (job-durability pattern)
    await db.commit()

    background_tasks.add_task(run_transcription, job_id=job_id, audio_bytes=audio_bytes, mime_type=effective_mime)

    return JSONResponse(status_code=202, content={"job_id": str(job_id)})
