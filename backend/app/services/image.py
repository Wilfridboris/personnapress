"""Image generation service.

Orchestrates featured image generation via Replicate's FLUX.1 [pro] model
and stores results in Supabase Storage.

Called ONLY from workers/generate.py and the regenerate endpoint (AR-19).
"""

import asyncio
import logging
import re
import uuid
from datetime import datetime, timezone

import sentry_sdk
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.repositories import generation_logs as generation_logs_repo
from app.db.repositories.models import Campaign, Client, Job, Subscription
from app.integrations import replicate as replicate_integration
from app.integrations import supabase_storage
from app.services import subscription_service

logger = logging.getLogger(__name__)

_IMAGE_REGEN_LIMIT = 3


def _build_image_prompt(blog_title: str, brand_voice_profile: dict | None) -> str:
    tone_descriptor = ""
    if brand_voice_profile:
        tone_list = brand_voice_profile.get("tone", [])
        tone_map = {
            "professional": "corporate editorial",
            "casual": "warm lifestyle",
            "formal": "minimalist clean",
            "friendly": "approachable human-centered",
            "authoritative": "bold editorial",
            "conversational": "relaxed lifestyle",
        }
        visual_tones = [tone_map.get(t.lower(), t) for t in tone_list[:2]]
        if visual_tones:
            tone_descriptor = ", ".join(visual_tones) + " style, "

    return (
        f"{tone_descriptor}featured blog image for '{blog_title}', "
        f"photorealistic, high resolution, 16:9 aspect ratio, "
        f"professional photography, no text overlay, clean background"
    )


async def _replicate_with_retry(prompt: str, max_retries: int = 3) -> str:
    """Call Replicate with exponential backoff (8s, 16s between attempts). Returns image URL."""
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            return await replicate_integration.generate_image(prompt)
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "_replicate_with_retry: attempt %d/%d failed: %s",
                attempt + 1,
                max_retries,
                exc,
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(8 * (2 ** attempt))  # 8s, 16s
    raise last_exc  # type: ignore[misc]


async def run_image_generation(
    campaign_id: uuid.UUID, job_id: uuid.UUID, db: AsyncSession
) -> None:
    """Generate featured image for a campaign and store in Supabase Storage.

    Steps:
      1. Subscription quota check.
      2. Build image prompt from blog H1 + brand tone.
      3. Call Replicate with retry.
      4. Download + re-upload to Supabase Storage.
      5. Update campaign.image_url, job.status=complete, generation_log.

    On image failure: job is set to complete (text content is done);
    error_details notes the image failure so the campaign can proceed.
    """
    # ── Step 1: Load campaign + client ────────────────────────────────────────
    campaign_result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = campaign_result.scalar_one_or_none()
    if not campaign:
        logger.error("run_image_generation: campaign %s not found", campaign_id)
        return

    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        logger.error("run_image_generation: job %s not found", job_id)
        return

    client_result = await db.execute(select(Client).where(Client.id == campaign.client_id))
    client = client_result.scalar_one_or_none()
    if not client:
        logger.error(
            "run_image_generation: client %s not found for campaign %s, cannot check quota",
            campaign.client_id,
            campaign_id,
        )
        job.status = "complete"
        job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        job.error_details = "Image generation failed — client record not found."
        await db.commit()
        return

    brand_voice_profile: dict | None = client.brand_voice_profile
    user_id = client.user_id

    # ── Step 2: Subscription check ────────────────────────────────────────────
    try:
        await subscription_service.check_image_limit(db, user_id)
    except HTTPException:
        logger.warning(
            "run_image_generation: image limit reached for user %s, skipping", user_id
        )
        job.status = "complete"
        job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()
        return

    # ── Step 3: Build prompt ──────────────────────────────────────────────────
    h1_match = re.search(
        r"<h1[^>]*>(.*?)</h1>", campaign.blog_html or "", re.IGNORECASE | re.DOTALL
    )
    blog_title_raw = h1_match.group(1).strip() if h1_match else "Untitled"
    blog_title = re.sub(r"<[^>]+>", "", blog_title_raw).strip() or "Untitled"
    prompt = _build_image_prompt(blog_title, brand_voice_profile)

    # ── Step 4: Call Replicate ────────────────────────────────────────────────
    try:
        replicate_url = await _replicate_with_retry(prompt)
    except Exception as exc:
        logger.exception(
            "run_image_generation: Replicate failed after retries for campaign %s: %s",
            campaign_id,
            exc,
        )
        sentry_sdk.capture_exception(exc)
        job.status = "complete"
        job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        job.error_details = "Image generation failed — blog and social posts are complete."
        await db.commit()
        return

    # ── Step 5: Download + re-upload to Supabase Storage ─────────────────────
    storage_path = f"generated-images/{campaign_id}/featured.png"
    try:
        public_url = await supabase_storage.upload_image_from_url(replicate_url, storage_path)
    except Exception as exc:
        logger.exception(
            "run_image_generation: Supabase upload failed for campaign %s: %s",
            campaign_id,
            exc,
        )
        sentry_sdk.capture_exception(exc)
        job.status = "complete"
        job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        job.error_details = "Image generation failed — blog and social posts are complete."
        await db.commit()
        return

    # ── Step 6: Update campaign + job + generation_log ───────────────────────
    campaign.image_url = public_url
    job.status = "complete"
    job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()

    if user_id:
        await generation_logs_repo.create_generation_log(
            db,
            user_id=user_id,
            campaign_id=campaign_id,
            replicate_count=1,
        )
        await db.commit()

    logger.info(
        "run_image_generation: image complete for campaign %s → %s", campaign_id, public_url
    )


async def regenerate_image(
    campaign_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> tuple[str, int]:
    """Regenerate the featured image for a campaign.

    Returns:
        (new_image_url, updated_image_regen_count)

    Raises:
        HTTPException 400 IMAGE_REGEN_LIMIT_REACHED if at limit.
        HTTPException 400 IMAGE_LIMIT_EXCEEDED if subscription quota exceeded.
    """
    campaign_result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = campaign_result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "CAMPAIGN_NOT_FOUND", "message": "Campaign not found.", "detail": {}}},
        )

    # Subscription quota check first (spec AC 3.4-5: quota before regen limit)
    await subscription_service.check_image_limit(db, user_id)

    # Regen count check
    if campaign.image_regen_count >= _IMAGE_REGEN_LIMIT:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "IMAGE_REGEN_LIMIT_REACHED",
                    "message": "0 regenerations remaining.",
                    "detail": {"limit": _IMAGE_REGEN_LIMIT},
                }
            },
        )

    # Build prompt
    client_result = await db.execute(select(Client).where(Client.id == campaign.client_id))
    client = client_result.scalar_one_or_none()
    brand_voice_profile: dict | None = client.brand_voice_profile if client else None

    h1_match = re.search(
        r"<h1[^>]*>(.*?)</h1>", campaign.blog_html or "", re.IGNORECASE | re.DOTALL
    )
    blog_title_raw = h1_match.group(1).strip() if h1_match else "Untitled"
    blog_title = re.sub(r"<[^>]+>", "", blog_title_raw).strip() or "Untitled"
    prompt = _build_image_prompt(blog_title, brand_voice_profile)

    # Call Replicate
    replicate_url = await _replicate_with_retry(prompt)

    # Upload to a version-specific path so the public URL changes with every
    # regeneration, busting the browser/CDN cache that would otherwise serve
    # the previous image (same URL → cached bytes, even after file overwrite).
    new_regen_count = campaign.image_regen_count + 1
    storage_path = f"generated-images/{campaign_id}/featured_{new_regen_count}.png"
    public_url = await supabase_storage.upload_image_from_url(replicate_url, storage_path)

    # Update campaign
    campaign.image_url = public_url
    campaign.image_regen_count += 1
    await db.commit()

    await generation_logs_repo.create_generation_log(
        db,
        user_id=user_id,
        campaign_id=campaign_id,
        replicate_count=1,
    )
    await db.commit()

    return public_url, campaign.image_regen_count
