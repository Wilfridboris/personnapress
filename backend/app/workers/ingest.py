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
from app.schemas.client import QuestionnaireRequest, ToneSliders
from app.services.ingestion import (
    ScrapingError,
    VoiceExtractionError,
    extract_file_text,
    extract_voice_profile,
    scrape_website,
)

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
    job.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
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
        # No content collected — questionnaire shown directly (AC5), not an extraction error
        job.status = "failed"
        job.error_details = "no_content"
        await db.commit()
        return

    combined_text = "\n\n---\n\n".join(all_text_parts)
    combined_text = combined_text[:MAX_TEXT_CHARS]

    # 6. Extract voice profile — calls Gemini with 3-retry logic (Story 2.5)
    try:
        voice_profile = await extract_voice_profile(combined_text, client.id, session=db)
    except VoiceExtractionError as exc:
        logger.exception(
            "ingest_worker: voice extraction failed for job %s: %s", job_id, exc
        )
        job.status = "failed"
        job.error_details = (
            "Voice profile extraction failed. Complete the questionnaire to set up your profile manually."
        )
        await db.commit()
        return
    except Exception as exc:
        logger.exception(
            "ingest_worker: unexpected voice extraction error for job %s: %s", job_id, exc
        )
        job.status = "failed"
        job.error_details = f"Voice extraction failed: {exc}"
        await db.commit()
        return

    # 7. Persist voice profile and complete the job
    client.brand_voice_profile = voice_profile if voice_profile else None
    job.status = "complete"
    job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
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


# ── Questionnaire tone slider → descriptor mapping ────────────────────────────

_SLIDER_TONE_MAP: dict[str, dict[int, str]] = {
    "formal_casual": {
        1: "formal",
        2: "somewhat formal",
        3: "balanced",
        4: "conversational",
        5: "casual",
    },
    "professional_friendly": {
        1: "professional",
        2: "business-like",
        3: "approachable",
        4: "friendly",
        5: "warm",
    },
    "concise_elaborate": {
        1: "concise",
        2: "direct",
        3: "balanced",
        4: "detailed",
        5: "thorough",
    },
}


def _sliders_to_tone_descriptors(tone_sliders: ToneSliders) -> list[str]:
    """Convert ToneSliders values to human-readable tone descriptor strings."""
    slider_dict = tone_sliders.model_dump()
    descriptors: list[str] = []
    for slider_key, mapping in _SLIDER_TONE_MAP.items():
        value = slider_dict.get(slider_key)
        if value is None:
            continue
        descriptor = mapping.get(max(1, min(5, int(value))))
        if descriptor:
            descriptors.append(descriptor)
    return descriptors


async def questionnaire_worker(
    job_id: uuid.UUID,
    client_id: uuid.UUID,
    questionnaire_data: "QuestionnaireRequest",
) -> None:
    """Process a voice questionnaire submission and extract a Brand Voice Profile.

    Converts slider values to tone descriptors, combines sample texts,
    then delegates to extract_voice_profile() for the Gemini call.
    """
    async with AsyncSessionLocal() as db:
        try:
            await _run_questionnaire(db, job_id, client_id, questionnaire_data)
        except Exception as exc:
            logger.exception(
                "questionnaire_worker: unhandled error for job %s", job_id
            )
            sentry_sdk.capture_exception(exc)
            await _mark_failed(db, job_id, str(exc))


async def _run_questionnaire(
    db: AsyncSession,
    job_id: uuid.UUID,
    client_id: uuid.UUID,
    data: "QuestionnaireRequest",
) -> None:
    # 1. Load and mark job in-progress
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        err = RuntimeError(f"questionnaire_worker: job {job_id} not found")
        logger.error("%s", err)
        sentry_sdk.capture_exception(err)
        return

    job.status = "in_progress"
    job.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(job)

    # 2. Convert slider values to tone descriptors
    tone_descriptors = _sliders_to_tone_descriptors(data.tone_sliders)

    # 3. Build combined text input
    text_parts: list[str] = []

    if tone_descriptors:
        text_parts.append(
            "TONE CONTEXT (from user preferences):\n"
            + ", ".join(tone_descriptors)
        )

    if data.sample_texts:
        non_empty = [t.strip() for t in data.sample_texts if t and t.strip()]
        if non_empty:
            text_parts.append("SAMPLE WRITING:\n" + "\n\n---\n\n".join(non_empty))

    if data.reference_urls:
        non_empty_urls = [u.strip() for u in data.reference_urls if u and u.strip()]
        if non_empty_urls:
            text_parts.append(
                "REFERENCE WRITERS (style inspirations):\n"
                + "\n".join(non_empty_urls)
            )

    if not text_parts:
        job.status = "failed"
        job.error_details = "No questionnaire data provided to analyze."
        await db.commit()
        return

    combined_text = "\n\n".join(text_parts)[:MAX_TEXT_CHARS]

    # 4. Extract voice profile via Gemini (3-retry, Sentry on failure)
    try:
        await extract_voice_profile(combined_text, client_id, session=db)
    except VoiceExtractionError as exc:
        logger.exception(
            "questionnaire_worker: voice extraction failed for job %s: %s", job_id, exc
        )
        job.status = "failed"
        job.error_details = (
            "Voice profile extraction failed. Complete the questionnaire to set up your profile manually."
        )
        await db.commit()
        return

    # 5. Mark job complete
    job.status = "complete"
    job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    logger.info(
        "questionnaire_worker: job %s completed for client %s", job_id, client_id
    )
