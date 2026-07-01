import uuid
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


async def get_active_ingestion_job_for_client(
    session: AsyncSession,
    client_id: uuid.UUID,
) -> Optional[Job]:
    result = await session.execute(
        select(Job)
        .where(Job.client_id == client_id)
        .where(Job.job_type == "ingestion")
        .where(Job.status.in_(["pending", "in_progress"]))
        .order_by(Job.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
