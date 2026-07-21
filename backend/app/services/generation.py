"""Content generation service.

Orchestrates the full text generation pipeline for a campaign:
blog post → voice fidelity check → social posts.

Called ONLY from workers/generate.py (AR-19). Never import gemini.py
directly from routers or workers — this module is the sole caller.
"""

import asyncio
import logging
import re
import uuid
from datetime import datetime, timezone

import sentry_sdk
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.db.repositories import generation_logs as generation_logs_repo
from app.db.repositories.models import Campaign, Client, Job

if settings.LLM_PROVIDER == "anthropic":
    from app.integrations import anthropic_client as _llm
else:
    from app.integrations import gemini as _llm  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# Thinking token budgets (NFR-9)
_BLOG_THINKING_TOKENS = 512
_FIDELITY_THINKING_TOKENS = 256
_SOCIAL_THINKING_TOKENS = 0
_ESTIMATED_TOTAL_TOKENS = _BLOG_THINKING_TOKENS + _FIDELITY_THINKING_TOKENS + _SOCIAL_THINKING_TOKENS

_RETRY_TRANSIENT_EXCEPTIONS: tuple[type[Exception], ...] = ()

try:
    from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
    _RETRY_TRANSIENT_EXCEPTIONS = (ServiceUnavailable, ResourceExhausted)
except ImportError:
    pass

try:
    from google.genai.errors import ClientError as _GenaiClientError

    def _is_transient_genai_error(exc: Exception) -> bool:
        return isinstance(exc, _GenaiClientError) and getattr(exc, "status_code", None) in (429, 503)
except ImportError:
    def _is_transient_genai_error(exc: Exception) -> bool:  # type: ignore[misc]
        return False

try:
    import anthropic as _anthropic_mod
    _RETRY_TRANSIENT_EXCEPTIONS_ANTHROPIC: tuple[type[Exception], ...] = (
        _anthropic_mod.RateLimitError,       # 429
        _anthropic_mod.InternalServerError,  # 500
        _anthropic_mod.OverloadedError,      # 529
    )
except ImportError:
    _RETRY_TRANSIENT_EXCEPTIONS_ANTHROPIC = ()


async def _llm_with_retry(fn, *args, max_retries: int = 4, **kwargs):
    """Call an async LLM function with exponential backoff on transient errors.

    Catches Gemini ServiceUnavailable/ResourceExhausted and Anthropic RateLimitError/InternalServerError.
    4 total attempts with 1s, 2s, 4s between them.
    Re-raises on max_retries exhaustion.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            return await fn(*args, **kwargs)
        except Exception as exc:
            if (
                (_RETRY_TRANSIENT_EXCEPTIONS and isinstance(exc, _RETRY_TRANSIENT_EXCEPTIONS))
                or _is_transient_genai_error(exc)
                or (_RETRY_TRANSIENT_EXCEPTIONS_ANTHROPIC and isinstance(exc, _RETRY_TRANSIENT_EXCEPTIONS_ANTHROPIC))
            ):
                last_exc = exc
                logger.warning(
                    "_llm_with_retry: transient error on attempt %d/%d: %s",
                    attempt + 1,
                    max_retries,
                    exc,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # 1s, 2s, 4s
            else:
                raise
    raise last_exc  # type: ignore[misc]


async def run_generation_pipeline(job_id: uuid.UUID, db: AsyncSession) -> None:
    """Execute the full text generation pipeline for a generation job.

    Steps:
      1. Load job + campaign + client (BVP); mark job in_progress.
      2. Generate blog HTML via LLM provider (512t, 3-retry).
      3. Run voice fidelity check (256t).
      4. Generate social posts (0t).
      5. Commit all campaign text fields in a single write.
      6. Log token usage to generation_logs.

    On unrecoverable error: sets job.status='failed' with error_details; logs to Sentry.
    Job is left in_progress after success (Story 3.4 image generation completes it).

    Args:
        job_id: UUID of the generation job record.
        db: Async SQLAlchemy session (caller owns lifecycle).
    """
    # ── Step 1: Load context ──────────────────────────────────────────────────
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        logger.error("run_generation_pipeline: job %s not found", job_id)
        sentry_sdk.capture_message(
            f"run_generation_pipeline: job {job_id} not found in DB", level="error"
        )
        return

    job.status = "in_progress"
    job.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(job)

    if not job.campaign_id:
        await _fail_job(db, job, "Generation job has no campaign_id")
        return

    campaign_result = await db.execute(
        select(Campaign).where(Campaign.id == job.campaign_id)
    )
    campaign = campaign_result.scalar_one_or_none()
    if not campaign:
        await _fail_job(db, job, f"Campaign {job.campaign_id} not found")
        return

    client_result = await db.execute(
        select(Client).where(Client.id == campaign.client_id)
    )
    client = client_result.scalar_one_or_none()
    brand_voice_profile: dict | None = client.brand_voice_profile if client else None

    try:
        # ── Step 2: Blog generation ───────────────────────────────────────────
        logger.info(
            "run_generation_pipeline: generating blog for campaign %s", campaign.id
        )
        blog_html: str = await _llm_with_retry(
            _llm.generate_blog,
            campaign.brain_dump,
            brand_voice_profile,
            _BLOG_THINKING_TOKENS,
            campaign.target_keyword,
            campaign.target_audience,
            campaign.secondary_keywords,
        )
        if not blog_html:
            raise ValueError("generate_blog returned empty content")
        campaign.blog_html = blog_html

        # ── Step 3: Voice fidelity check ─────────────────────────────────────
        h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", blog_html, re.IGNORECASE | re.DOTALL)
        blog_title_raw = h1_match.group(1).strip() if h1_match else "Untitled"
        blog_title = re.sub(r"<[^>]+>", "", blog_title_raw).strip() or "Untitled"

        voice_score: dict = await _llm_with_retry(
            _llm.check_fidelity,
            blog_html,
            brand_voice_profile,
            _FIDELITY_THINKING_TOKENS,
        )
        campaign.voice_score = voice_score

        # ── Step 4: Social post generation ───────────────────────────────────
        logger.info(
            "run_generation_pipeline: generating social posts for campaign %s",
            campaign.id,
        )
        social: dict = await _llm_with_retry(
            _llm.generate_social,
            campaign.brain_dump,
            blog_title,
            brand_voice_profile,
            _SOCIAL_THINKING_TOKENS,
        )
        campaign.x_post = social["x_post"]
        campaign.linkedin_post = social["linkedin_post"]

        # ── Step 5: Single atomic DB write ────────────────────────────────────
        await db.commit()
        logger.info(
            "run_generation_pipeline: campaign %s text content committed", campaign.id
        )

        # ── Step 6: Log token usage ───────────────────────────────────────────
        user_id = client.user_id if client else None
        if user_id:
            await generation_logs_repo.create_generation_log(
                db,
                user_id=user_id,
                campaign_id=campaign.id,
                gemini_tokens=_ESTIMATED_TOTAL_TOKENS,
            )
            await db.commit()

        # Job stays in_progress — Story 3.4 image generation completes it.
        logger.info(
            "run_generation_pipeline: text generation complete for job %s "
            "(image generation pending via Story 3.4)",
            job_id,
        )

    except Exception as exc:
        logger.exception(
            "run_generation_pipeline: unrecoverable error for job %s: %s", job_id, exc
        )
        sentry_sdk.capture_exception(exc)
        await _fail_job(db, job, "Generation service temporarily unavailable. Retry in a few minutes.")


async def _fail_job(db: AsyncSession, job: Job, error_details: str) -> None:
    """Mark a job as failed with the given error details and commit."""
    try:
        await db.rollback()
    except Exception:
        logger.warning("_fail_job: rollback failed for job %s", job.id, exc_info=True)
    try:
        job.status = "failed"
        job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        job.error_details = error_details
        await db.commit()
        logger.error("run_generation_pipeline: job %s failed: %s", job.id, error_details)
    except Exception:
        logger.exception(
            "run_generation_pipeline: could not mark job %s as failed", job.id
        )
