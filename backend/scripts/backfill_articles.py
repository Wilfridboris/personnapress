"""Backfill articles for already-published campaigns.

Run from the backend/ directory:
    python -m scripts.backfill_articles

Creates an article (status=hidden) for every published campaign that has
blog_html and no existing article. Re-running is safe — per-campaign
idempotency ensures no duplicates.
"""

import asyncio
import logging

from sqlalchemy import select

from app.db.connection import get_session_context
from app.db.repositories.models import Article, Campaign, CampaignStatus
from app.services.articles import create_or_update_article_from_campaign

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run() -> None:
    created = 0
    skipped = 0

    async with get_session_context() as session:
        result = await session.execute(
            select(Campaign).where(
                Campaign.status == CampaignStatus.published,
                Campaign.blog_html.isnot(None),
                Campaign.blog_html != "",
            )
        )
        campaigns = list(result.scalars().all())

        for campaign in campaigns:
            existing_result = await session.execute(
                select(Article).where(Article.campaign_id == campaign.id)
            )
            if existing_result.scalar_one_or_none() is not None:
                skipped += 1
                continue

            try:
                await create_or_update_article_from_campaign(
                    session, campaign, status_override="hidden"
                )
                await session.commit()
                created += 1
            except Exception:
                logger.error("Failed to backfill article for campaign=%s", campaign.id, exc_info=True)
                await session.rollback()

    print(f"Backfill complete: {created} created, {skipped} skipped.")


if __name__ == "__main__":
    asyncio.run(run())
