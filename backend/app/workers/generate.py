"""Content generation worker.

Receives the job_id from the router's BackgroundTask and runs the full
text + image generation pipeline. Creates its own DB session (the
request-scoped session is closed before BackgroundTasks execute).
"""

import logging
import uuid

import sentry_sdk

from app.db.connection import AsyncSessionLocal
from app.db.repositories.jobs import get_job
from app.services import generation as generation_service
from app.services import image as image_service

logger = logging.getLogger(__name__)


async def run_generation(job_id: uuid.UUID) -> None:
    """Entry point called by the BackgroundTask dispatcher."""
    try:
        async with AsyncSessionLocal() as db:
            # Text generation (Story 3.3)
            await generation_service.run_generation_pipeline(job_id, db)

            # Image generation (Story 3.4) — runs only after text succeeds
            job = await get_job(db, job_id)
            if job and job.status == "in_progress" and job.campaign_id:
                await image_service.run_image_generation(job.campaign_id, job_id, db)
    except Exception as exc:
        logger.exception("run_generation: unhandled error for job %s", job_id)
        sentry_sdk.capture_exception(exc)
