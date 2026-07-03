import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.db.connection import get_session
from app.db.repositories.models import Campaign, Client, Job
from app.schemas.job import JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])

_INVALID_SESSION = {"error": {"code": "INVALID_SESSION", "message": "Invalid session.", "detail": {}}}


@router.get("/{job_id}", response_model=JobResponse)
@limiter.limit("60/minute")
async def get_job(
    request: Request,
    job_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> JobResponse:
    try:
        user_id = uuid.UUID(current_user["user_id"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail=_INVALID_SESSION)

    _not_found = HTTPException(
        status_code=404,
        detail={"error": {"code": "JOB_NOT_FOUND", "message": "Job not found.", "detail": {}}},
    )

    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise _not_found

    if job.client_id:
        client_result = await db.execute(select(Client).where(Client.id == job.client_id))
        client = client_result.scalar_one_or_none()
        if not client or client.user_id != user_id:
            raise _not_found
    elif job.campaign_id:
        # Campaign-level jobs: verify ownership via campaign → client → user
        campaign_result = await db.execute(
            select(Campaign).where(Campaign.id == job.campaign_id)
        )
        campaign = campaign_result.scalar_one_or_none()
        if campaign:
            client_result = await db.execute(
                select(Client).where(Client.id == campaign.client_id)
            )
            client = client_result.scalar_one_or_none()
            if not client or client.user_id != user_id:
                raise _not_found

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
