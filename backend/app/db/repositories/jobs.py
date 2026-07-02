import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.repositories.models import Job


async def create_job(
    session: AsyncSession,
    job_type: str,
    status: str,
    campaign_id: Optional[uuid.UUID] = None,
    client_id: Optional[uuid.UUID] = None,
) -> Job:
    job = Job(job_type=job_type, status=status, campaign_id=campaign_id, client_id=client_id)
    session.add(job)
    await session.flush()
    await session.refresh(job)
    return job


async def get_job(session: AsyncSession, job_id: uuid.UUID) -> Optional[Job]:
    result = await session.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()


async def update_job_status(
    session: AsyncSession,
    job_id: uuid.UUID,
    status: str,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
    error_details: Optional[str] = None,
) -> Optional[Job]:
    job = await get_job(session, job_id)
    if not job:
        return None
    job.status = status
    if started_at is not None:
        job.started_at = started_at
    if completed_at is not None:
        job.completed_at = completed_at
    if error_details is not None:
        job.error_details = error_details
    await session.flush()
    await session.refresh(job)
    return job


async def get_active_ingestion_job_for_client(
    session: AsyncSession,
    client_id: uuid.UUID,
) -> Optional[Job]:
    result = await session.execute(
        select(Job)
        .where(Job.client_id == client_id)
        .where(Job.job_type.in_(["ingestion", "questionnaire"]))
        .where(Job.status.in_(["pending", "in_progress"]))
        .order_by(Job.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_latest_voice_job_for_client(
    session: AsyncSession,
    client_id: uuid.UUID,
) -> Optional[Job]:
    """Return the most recently created ingestion or questionnaire job for a client.

    Unlike get_active_ingestion_job_for_client this includes all statuses so callers
    can detect a previous failed extraction attempt.
    """
    result = await session.execute(
        select(Job)
        .where(Job.client_id == client_id)
        .where(Job.job_type.in_(["ingestion", "questionnaire"]))
        .order_by(Job.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
