"""Roadmap generation service.

Orchestrates multi-post generation for a content roadmap (Epic 20).
This is the ONLY place that creates campaigns in bulk for a roadmap.
Delegates text generation to services/generation.py and image generation
to services/image.py. No business logic in routers. (AR-19)
"""

import logging
import uuid
from datetime import datetime, timezone

import sentry_sdk
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.repositories.jobs import create_job
from app.db.repositories.models import Campaign, Client, CampaignStatus, Roadmap, RoadmapStatus
from app.services import generation as generation_service
from app.services import image as image_service
from app.services.generation import run_generation_pipeline
from app.services.subscription_service import check_image_limit_batch

logger = logging.getLogger(__name__)


async def generate_roadmap(roadmap_id: uuid.UUID, db: AsyncSession) -> None:
    """Execute the full generation pipeline for a roadmap.

    Steps:
      1. Load Roadmap row; set status=generating.
      2. Load Client BVP.
      3. Check batch image quota (non-raising).
      4. For each post slot: blog + social (via run_generation_pipeline) or
         social-only (via generate_social_only).
      5. Generate images for the first allowed_images campaigns.
      6. Set Roadmap.status=ready on success; failed on error.
    """
    # ── Step 1: Load and mark generating ────────────────────────────────────
    result = await db.execute(select(Roadmap).where(Roadmap.id == roadmap_id))
    roadmap = result.scalar_one_or_none()
    if not roadmap:
        logger.error("generate_roadmap: roadmap %s not found", roadmap_id)
        return

    roadmap.status = RoadmapStatus.generating
    roadmap.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()

    # ── Step 2: Load client and BVP ─────────────────────────────────────────
    client_result = await db.execute(select(Client).where(Client.id == roadmap.client_id))
    client = client_result.scalar_one_or_none()
    bvp: dict | None = client.brand_voice_profile if client else None
    user_id = roadmap.user_id

    try:
        # ── Step 3: Determine image quota ────────────────────────────────────
        roadmap_config = client.roadmap_config if client else {}
        config = roadmap_config or {}

        linkedin_count: int = config.get("linkedin_count", 0)
        twitter_count: int = config.get("twitter_count", 0)
        blog_enabled: bool = not roadmap.skip_blog

        total_posts = twitter_count + linkedin_count + (1 if blog_enabled else 0)
        generate_images = roadmap.generate_images and config.get("images_enabled", True)

        if generate_images and total_posts > 0:
            allowed_images, _ = await check_image_limit_batch(db, user_id, total_posts)
        else:
            allowed_images = 0

        # Track generated campaigns in order for image assignment
        campaign_ids: list[uuid.UUID] = []
        title_hints: list[str] = []

        # ── Step 4: Blog + social slot ────────────────────────────────────────
        if blog_enabled:
            blog_campaign = Campaign(
                client_id=roadmap.client_id,
                brain_dump=roadmap.brain_dump,
                status=CampaignStatus.pending_approval,
                roadmap_id=roadmap_id,
            )
            db.add(blog_campaign)
            await db.flush()
            await db.refresh(blog_campaign)

            job = await create_job(
                db,
                job_type="generate",
                status="pending",
                campaign_id=blog_campaign.id,
            )
            await db.commit()

            await run_generation_pipeline(job.id, db)

            # Reload to get updated title
            await db.refresh(blog_campaign)
            campaign_ids.append(blog_campaign.id)
            title_hints.append(_extract_title(blog_campaign.blog_html or ""))

        # ── Twitter-only slots ────────────────────────────────────────────────
        for i in range(twitter_count):
            x_campaign = Campaign(
                client_id=roadmap.client_id,
                brain_dump=roadmap.brain_dump,
                status=CampaignStatus.pending_approval,
                roadmap_id=roadmap_id,
            )
            db.add(x_campaign)
            await db.flush()
            await db.refresh(x_campaign)
            await db.commit()

            await generation_service.generate_social_only(
                roadmap.brain_dump, bvp, "x", x_campaign.id, db
            )

            campaign_ids.append(x_campaign.id)
            title_hints.append(f"Roadmap X post {i + 1}")

        # ── LinkedIn-only slots ───────────────────────────────────────────────
        for i in range(linkedin_count):
            li_campaign = Campaign(
                client_id=roadmap.client_id,
                brain_dump=roadmap.brain_dump,
                status=CampaignStatus.pending_approval,
                roadmap_id=roadmap_id,
            )
            db.add(li_campaign)
            await db.flush()
            await db.refresh(li_campaign)
            await db.commit()

            await generation_service.generate_social_only(
                roadmap.brain_dump, bvp, "linkedin", li_campaign.id, db
            )

            campaign_ids.append(li_campaign.id)
            title_hints.append(f"Roadmap LinkedIn post {i + 1}")

        # ── Step 5: Generate images for first allowed_images campaigns ────────
        if generate_images and allowed_images > 0:
            for idx, cid in enumerate(campaign_ids[:allowed_images]):
                hint = title_hints[idx] if idx < len(title_hints) else "Untitled"
                await image_service.generate_image_for_roadmap_campaign(cid, user_id, hint, db)

        # ── Step 6: Mark ready ────────────────────────────────────────────────
        roadmap.status = RoadmapStatus.ready
        roadmap.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()
        logger.info("generate_roadmap: roadmap %s complete (%d campaigns)", roadmap_id, len(campaign_ids))

    except Exception as exc:
        logger.exception("generate_roadmap: unrecoverable error for roadmap %s: %s", roadmap_id, exc)
        sentry_sdk.capture_exception(exc)
        try:
            await db.rollback()
        except Exception:
            pass
        try:
            result2 = await db.execute(select(Roadmap).where(Roadmap.id == roadmap_id))
            roadmap2 = result2.scalar_one_or_none()
            if roadmap2:
                roadmap2.status = RoadmapStatus.failed
                roadmap2.error_message = str(exc)[:500]
                roadmap2.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                await db.commit()
        except Exception:
            logger.exception("generate_roadmap: could not mark roadmap %s as failed", roadmap_id)


def _extract_title(blog_html: str) -> str:
    """Extract plain text from the first H1 in blog HTML."""
    import re
    h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", blog_html, re.IGNORECASE | re.DOTALL)
    if not h1_match:
        return "Untitled"
    raw = h1_match.group(1).strip()
    return re.sub(r"<[^>]+>", "", raw).strip() or "Untitled"
