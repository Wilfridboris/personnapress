import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.connection import AsyncSessionLocal
from app.db.repositories.models import Job

logger = logging.getLogger(__name__)


async def ingest_worker(job_id: uuid.UUID, client_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                logger.error("ingest_worker: job %s not found", job_id)
                return

            job.status = "in_progress"
            job.started_at = datetime.now(timezone.utc)
            await db.commit()

            # Full scraping implemented in Story 2.4; stub immediately completes the job
            logger.info("ingest_worker: job %s started for client %s (stub)", job_id, client_id)
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()

        except Exception as exc:
            logger.exception("ingest_worker: unhandled error for job %s", job_id)
            try:
                await db.rollback()
                result2 = await db.execute(select(Job).where(Job.id == job_id))
                job2 = result2.scalar_one_or_none()
                if job2:
                    job2.status = "failed"
                    job2.error_details = str(exc)
                    await db.commit()
            except Exception:
                logger.exception("ingest_worker: failed to mark job %s as failed", job_id)
