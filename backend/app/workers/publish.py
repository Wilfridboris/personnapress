"""Multi-platform publish worker.

Receives job_id and campaign_id from the router's BackgroundTask and runs
dispatch_publish. Creates its own DB session (the request-scoped session is
closed before BackgroundTasks execute).
"""

import json
import logging
from uuid import UUID

from app.db.connection import get_session_context
from app.db.repositories.campaigns import update_campaign_status
from app.db.repositories.jobs import update_job
from app.db.repositories.models import utcnow
from app.services.publishing import dispatch_publish

logger = logging.getLogger(__name__)


async def run_publish(job_id: UUID, campaign_id: UUID) -> None:
    """BackgroundTask entry point for multi-platform publishing."""
    async with get_session_context() as db:
        await update_job(db, job_id, status="in_progress", started_at=utcnow())
        await db.commit()
        try:
            results = await dispatch_publish(db, campaign_id, job_id)
            all_success = all(v == "success" for v in results.values()) and bool(results)
            if all_success:
                await update_campaign_status(db, campaign_id, "published")
                await update_job(db, job_id, status="complete", completed_at=utcnow())
            else:
                await update_campaign_status(db, campaign_id, "failed")
                await update_job(
                    db,
                    job_id,
                    status="failed",
                    error_details=json.dumps(results),
                    completed_at=utcnow(),
                )
            await db.commit()
        except Exception as exc:
            logger.error("Fatal publish error job=%s: %s", job_id, exc, exc_info=True)
            await update_campaign_status(db, campaign_id, "failed")
            await update_job(
                db,
                job_id,
                status="failed",
                error_details=json.dumps({"error": str(exc)}),
                completed_at=utcnow(),
            )
            await db.commit()
