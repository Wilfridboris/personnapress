import uuid
from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.models import PublishedPost, utcnow


async def upsert_published_post(
    session: AsyncSession,
    *,
    campaign_id: uuid.UUID,
    client_id: uuid.UUID,
    platform: str,
    platform_post_id: str,
    permalink: Optional[str],
    published_at: datetime,
) -> None:
    """Insert or update a published_posts row for (campaign_id, platform).

    Re-publish of the same campaign+platform UPSERTs the latest id and permalink.
    """
    stmt = (
        pg_insert(PublishedPost)
        .values(
            id=uuid.uuid4(),
            campaign_id=campaign_id,
            client_id=client_id,
            platform=platform,
            platform_post_id=platform_post_id,
            permalink=permalink,
            published_at=published_at,
            created_at=utcnow(),
        )
        .on_conflict_do_update(
            index_elements=["campaign_id", "platform"],
            set_={
                "platform_post_id": platform_post_id,
                "permalink": permalink,
                "published_at": published_at,
            },
        )
    )
    try:
        await session.execute(stmt)
        await session.commit()
    except Exception:
        await session.rollback()
        raise


async def get_published_posts_for_campaign(
    session: AsyncSession,
    campaign_id: uuid.UUID,
) -> list[PublishedPost]:
    """Return all published_posts rows for a campaign (used by analytics story 24-2)."""
    result = await session.execute(
        sa.select(PublishedPost).where(PublishedPost.campaign_id == campaign_id)
    )
    return list(result.scalars().all())
