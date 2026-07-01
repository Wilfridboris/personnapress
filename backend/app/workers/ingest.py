"""Brand voice ingestion worker.

Orchestrates website scraping, file text extraction, and voice profile
extraction for a client ingestion job.
"""

import logging
import uuid
from datetime import datetime, timezone

import sentry_sdk
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.connection import AsyncSessionLocal
from app.db.repositories.models import Client, Job
from app.integrations import supabase_storage
from app.services.ingestion import ScrapingError, extract_file_text, extract_voice_profile, scrape_website

logger = logging.getLogger(__name__)

MAX_TEXT_CHARS = 50_000


async def ingest_worker(job_id: uuid.UUID, client_id: uuid.UUID) -> None:
    """Full ingestion pipeline: scrape website, extract file text, derive voice profile."""
    async with AsyncSessionLocal() as db:
        try:
            await _run_ingestion(db, job_id, client_id)
        except Exception as exc:
            logger.exception("ingest_worker: unhandled error for job %s", job_id)
            sentry_sdk.capture_exception(exc)
            await _mark_failed(db, job_id, str(exc))


async def _run_ingestion(db: AsyncSession, job_id: uuid.UUID, client_id: uuid.UUID) -> None:
    # 1. Load and mark job in-progress
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        logger.error("ingest_worker: job %s not found", job_id)
        return

    job.status = "in_progress"
    job.started_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(job)

    # 2. Load client record
    client_result = await db.execute(select(Client).where(Client.id == client_id))
    client = client_result.scalar_one_or_none()
    if not client:
        logger.error("ingest_worker: client %s not found for job %s", client_id, job_id)
        job.status = "failed"
        job.error_details = f"Client {client_id} not found"
        await db.commit()
        return

    # 3. Scrape website (if URL set) — failure does NOT abort the job
    scraped_text = ""
    if client.website_url:
        try:
            scraped_text = await scrape_website(client.website_url)
            logger.info(
                "ingest_worker: scraped %d chars from %s for job %s",
                len(scraped_text),
                client.website_url,
                job_id,
            )
        except ScrapingError as exc:
            logger.warning("ingest_worker: scraping failed for job %s: %s", job_id, exc)
            # Continue with file text only
        except Exception as exc:
            logger.warning(
                "ingest_worker: unexpected scraping error for job %s: %s", job_id, exc
            )
            # Continue with file text only

    # 4. Download and extract text from uploaded files
    file_texts: list[str] = []
    try:
        file_list = await supabase_storage.list_files(
            "brand-content", f"{client_id}/"
        )
        for file_info in file_list:
            filename = file_info.get("name", "")
            if not filename:
                continue
            try:
                file_bytes = await supabase_storage.download_file(
                    "brand-content", f"{client_id}/{filename}"
                )
                text = extract_file_text(file_bytes, filename)
                if text:
                    file_texts.append(text)
            except Exception as exc:
                logger.warning(
                    "ingest_worker: failed to process file %s for job %s: %s",
                    filename,
                    job_id,
                    exc,
                )
    except Exception as exc:
        logger.warning(
            "ingest_worker: failed to list/download files for job %s: %s", job_id, exc
        )

    # 5. Assemble combined text
    all_text_parts = list(filter(None, [scraped_text] + file_texts))
    if not all_text_parts:
        job.status = "failed"
        job.error_details = (
            f"No text could be extracted from {client.website_url or 'uploaded files'}. "
            "Please complete the voice questionnaire."
        )
        await db.commit()
        return

    combined_text = "\n\n---\n\n".join(all_text_parts)
    combined_text = combined_text[:MAX_TEXT_CHARS]

    # 6. Extract voice profile (Story 2.5 — stub returns {} until implemented)
    try:
        voice_profile = await extract_voice_profile(combined_text, client.id)
    except Exception as exc:
        logger.exception(
            "ingest_worker: voice extraction failed for job %s: %s", job_id, exc
        )
        job.status = "failed"
        job.error_details = f"Voice extraction failed: {exc}"
        await db.commit()
        return

    # 7. Persist voice profile and complete the job
    client.brand_voice_profile = voice_profile if voice_profile else None
    job.status = "completed"
    job.completed_at = datetime.now(timezone.utc)
    await db.commit()
    logger.info("ingest_worker: job %s completed for client %s", job_id, client_id)


async def _mark_failed(db: AsyncSession, job_id: uuid.UUID, error: str) -> None:
    """Best-effort: mark the job as failed with error_details."""
    try:
        await db.rollback()
        async with AsyncSessionLocal() as fresh_db:
            result = await fresh_db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if job:
                job.status = "failed"
                job.error_details = error
                await fresh_db.commit()
    except Exception:
        logger.exception("ingest_worker: could not mark job %s as failed", job_id)
