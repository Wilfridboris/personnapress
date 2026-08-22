import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.models import PostMetric


async def bulk_insert_snapshots(
    session: AsyncSession,
    snapshots: list["MetricSnapshotRow"],
) -> None:
    """Append-only INSERT of MetricSnapshot rows into post_metrics. Never UPDATEs."""
    for snap in snapshots:
        row = PostMetric(
            published_post_id=snap.published_post_id,
            client_id=snap.client_id,
            platform=snap.platform,
            captured_at=snap.captured_at,
            impressions=snap.impressions,
            engagements=snap.engagements,
            likes=snap.likes,
            comments=snap.comments,
            shares=snap.shares,
            raw=snap.raw,
            unavailable_reason=snap.unavailable_reason,
        )
        session.add(row)
    await session.flush()


async def latest_per_post(
    session: AsyncSession,
    published_post_ids: list[uuid.UUID],
) -> list[PostMetric]:
    """Return the most-recent snapshot for each published_post_id (DISTINCT ON).

    Used by Story 24-3 to display current metrics per post.
    """
    if not published_post_ids:
        return []
    result = await session.execute(
        text(
            """
            SELECT DISTINCT ON (published_post_id) *
            FROM post_metrics
            WHERE published_post_id = ANY(:ids)
            ORDER BY published_post_id, captured_at DESC
            """
        ),
        {"ids": [str(pid) for pid in published_post_ids]},
    )
    rows = result.mappings().all()
    return [PostMetric(**dict(r)) for r in rows]


async def series(
    session: AsyncSession,
    published_post_id: uuid.UUID,
    since: Optional[datetime] = None,
) -> list[PostMetric]:
    """Return all snapshots for a single post in chronological order.

    Used by Story 24-3 to build trend sparklines.
    """
    if since is not None:
        result = await session.execute(
            text(
                """
                SELECT * FROM post_metrics
                WHERE published_post_id = :pid AND captured_at >= :since
                ORDER BY captured_at ASC
                """
            ),
            {"pid": str(published_post_id), "since": since},
        )
    else:
        result = await session.execute(
            text(
                """
                SELECT * FROM post_metrics
                WHERE published_post_id = :pid
                ORDER BY captured_at ASC
                """
            ),
            {"pid": str(published_post_id)},
        )
    rows = result.mappings().all()
    return [PostMetric(**dict(r)) for r in rows]


# Type alias used by bulk_insert_snapshots — resolved at runtime from meta_metrics module
class MetricSnapshotRow:
    """Protocol-compatible duck type — accepts MetricSnapshot dataclass from integrations."""
    published_post_id: uuid.UUID
    client_id: uuid.UUID
    platform: str
    captured_at: datetime
    impressions: Optional[int]
    engagements: Optional[int]
    likes: Optional[int]
    comments: Optional[int]
    shares: Optional[int]
    raw: dict
    unavailable_reason: Optional[str]
