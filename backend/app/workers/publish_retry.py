"""Retry worker for single-platform publish failures."""

import json
import logging
from uuid import UUID

from app.db.connection import get_session_context
from app.db.repositories.campaigns import update_campaign_status
from app.db.repositories.jobs import get_job, update_job
from app.db.repositories.models import utcnow
from app.services.publishing import dispatch_publish_for_platform

logger = logging.getLogger(__name__)


async def run_publish_retry(job_id: UUID, campaign_id: UUID, platform: str) -> None:
    """BackgroundTask: retry publishing for a single failed platform."""
    async with get_session_context() as db:
        await update_job(db, job_id, status="in_progress", started_at=utcnow())
        await db.commit()
        try:
            job = await get_job(db, job_id)
            if job is None:
                logger.error("run_publish_retry: job %s not found", job_id)
                return
            existing = json.loads(job.error_details or "{}")
            result = await dispatch_publish_for_platform(db, campaign_id, platform)
            merged = {**existing, **result}
            all_success = all(v == "success" for v in merged.values()) and bool(merged)

            if all_success:
                await update_campaign_status(db, campaign_id, "published")
                await update_job(db, job_id, status="complete", error_details=None, completed_at=utcnow())
            else:
                await update_campaign_status(db, campaign_id, "failed")
                await update_job(
                    db,
                    job_id,
                    status="failed",
                    error_details=json.dumps(merged),
                    completed_at=utcnow(),
                )
            await db.commit()
        except Exception as exc:
            logger.error("Fatal retry error job=%s: %s", job_id, exc, exc_info=True)
            try:
                await update_campaign_status(db, campaign_id, "failed")
                await update_job(
                    db,
                    job_id,
                    status="failed",
                    error_details=json.dumps({platform: f"Unexpected error — {str(exc)[:100]}"}),
                    completed_at=utcnow(),
                )
                await db.commit()
            except Exception:
                logger.exception("Failed to record retry error for job=%s", job_id)
