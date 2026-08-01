"""Content generation worker.

Receives the job_id from the router's BackgroundTask and runs the full
text + image generation pipeline. Creates its own DB session (the
request-scoped session is closed before BackgroundTasks execute).
"""

import logging
import uuid
from datetime import datetime, timezone

import sentry_sdk

from app.db.connection import AsyncSessionLocal
from app.db.repositories.campaigns import get_campaign
from app.db.repositories.jobs import get_job
from app.services import generation as generation_service
from app.services import image as image_service

logger = logging.getLogger(__name__)


async def run_generation(job_id: uuid.UUID) -> None:
    """Entry point called by the BackgroundTask dispatcher."""
    try:
        async with AsyncSessionLocal() as db:
            job = await get_job(db, job_id)
            if not job or job.status != "pending":
                logger.warning(
                    "run_generation: job %s skipped (status=%s)",
                    job_id,
                    job.status if job else "not found",
                )
                return

            campaign = await get_campaign(db, job.campaign_id) if job.campaign_id else None
            campaign_type = campaign.campaign_type if campaign else "blog_full"

            if campaign_type == "social_only":
                await generation_service.run_social_only_pipeline(job_id, db)
            else:
                # Full pipeline: text then image
                await generation_service.run_generation_pipeline(job_id, db)

                # Image generation — runs only after text succeeds and skip_image is False
                job = await get_job(db, job_id)
                if job and job.status == "in_progress" and job.campaign_id:
                    campaign_check = await get_campaign(db, job.campaign_id)
                    if campaign_check and campaign_check.skip_image:
                        job.status = "complete"
                        job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                        await db.commit()
                        logger.info(
                            "run_generation: skip_image=True, image skipped for campaign %s",
                            job.campaign_id,
                        )
                    else:
                        await image_service.run_image_generation(job.campaign_id, job_id, db)
    except Exception as exc:
        logger.exception("run_generation: unhandled error for job %s", job_id)
        sentry_sdk.capture_exception(exc)
