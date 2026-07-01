import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.dependencies import get_current_user
from app.db.connection import get_session
from app.db.repositories.models import Client, Job
from app.schemas.job import JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])

_INVALID_SESSION = {"error": {"code": "INVALID_SESSION", "message": "Invalid session.", "detail": {}}}


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> JobResponse:
    try:
        user_id = uuid.UUID(current_user["user_id"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail=_INVALID_SESSION)

    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail={"error": {"code": "JOB_NOT_FOUND", "message": "Job not found.", "detail": {}}})

    if job.client_id:
        client_result = await db.execute(select(Client).where(Client.id == job.client_id))
        client = client_result.scalar_one_or_none()
        if not client or client.user_id != user_id:
            raise HTTPException(status_code=404, detail={"error": {"code": "JOB_NOT_FOUND", "message": "Job not found.", "detail": {}}})

    return JobResponse(
        id=job.id,
        campaign_id=job.campaign_id,
        client_id=job.client_id,
        job_type=job.job_type,
        status=job.status,
        scheduled_at=job.scheduled_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        attempt_count=job.attempt_count,
        error_details=job.error_details,
        created_at=job.created_at,
    )
