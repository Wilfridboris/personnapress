"""metrics_poll — scheduled sweep that collects Meta post engagement snapshots.

Architecture position: write side of the CQRS-lite split (AD-A1, AD-A10).
  scheduler -> workers/analytics.py -> integrations/meta_metrics.py -> repositories/post_metrics.py

Fault-isolation (AD-A10): one post/platform failure is caught per item, logged to
  Sentry, and skipped. The sweep always marks the job complete regardless of individual
  fetch outcomes; failed items are retried on the next cadence firing.

Concurrency (AD-A2): I/O-bound await httpx only; holds one batch of ids + JSON in
  memory at a time; no dataframe stack; co-exists with generation on 1 vCPU / 1 GB.

Credentials: only this worker calls decrypt_credential() for analytics reads. Decrypted
  creds are never logged and go out of scope after the per-client batch completes.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import sentry_sdk
from sqlalchemy import select, text

from app.core.config import settings
from app.core.security import decrypt_credential
from app.db.connection import async_session_factory
from app.db.repositories.jobs import create_job, update_job
from app.db.repositories.models import PublishedPost, utcnow
from app.db.repositories.platform_connections import get_connection_for_platform
from app.db.repositories.post_metrics import bulk_insert_snapshots
from app.integrations import meta_metrics

logger = logging.getLogger(__name__)

# ── Decaying cadence (AD-A6) ──────────────────────────────────────────────────
# For Meta reads (free), the cadence bounds DB growth rather than cost.
# Format: (max_age, poll_interval) — a post is "due" if it falls in this age bucket
# and its last snapshot is older than the interval.
# Tune this constant; it is the single knob for polling frequency.
CADENCE: list[tuple[timedelta, timedelta]] = [
    (timedelta(hours=24), timedelta(hours=1)),   # first 24 h: poll every hour
    (timedelta(days=7),   timedelta(days=1)),    # day 1-7:   poll daily
    (timedelta(days=90),  timedelta(weeks=1)),   # day 7-90:  poll weekly
    # beyond 90 days: no longer polled (post not returned by select_due_meta_posts)
]

# Meta platforms handled by this worker
_META_PLATFORMS = ("facebook_page", "instagram", "threads")


def is_due(
    published_at: datetime,
    last_captured_at: Optional[datetime],
    now: datetime,
) -> bool:
    """Return True if a post should be polled in this sweep.

    A post is due when:
    - Its age falls within a cadence bucket (age < 90 days), AND
    - Either it has never been polled (last_captured_at is None), OR
      last_captured_at + bucket_interval <= now
    """
    age = now - published_at
    for max_age, interval in CADENCE:
        if age < max_age:
            if last_captured_at is None:
                return True
            return (last_captured_at + interval) <= now
    return False  # beyond 90-day horizon


# ── Entry point ───────────────────────────────────────────────────────────────

async def metrics_poll() -> None:
    """APScheduler entry point. Writes a jobs row then runs the sweep."""
    if not settings.ANALYTICS_ENABLED:
        return
    async with async_session_factory() as db:
        job = await create_job(db, job_type="metrics_poll", status="in_progress")
        await db.commit()

        try:
            await _run_sweep(db)
            await update_job(db, job.id, status="complete", completed_at=utcnow())
            await db.commit()
        except Exception as exc:
            logger.error("metrics_poll sweep failed: %s", exc, exc_info=True)
            sentry_sdk.capture_exception(exc)
            await update_job(db, job.id, status="failed", completed_at=utcnow())
            await db.commit()


async def _run_sweep(db) -> None:
    """Select due Meta posts, resolve creds per client, fetch, and bulk-insert snapshots."""
    now = datetime.now(timezone.utc)

    due_posts = await _select_due_meta_posts(db, now)
    if not due_posts:
        logger.info("metrics_poll: no due posts")
        return

    logger.info("metrics_poll: %d posts due", len(due_posts))

    # Group by (client_id, platform) to minimise connection lookups
    by_client_platform: dict[tuple[uuid.UUID, str], list] = {}
    for post in due_posts:
        key = (post.client_id, post.platform)
        by_client_platform.setdefault(key, []).append(post)

    for (client_id, platform), posts in by_client_platform.items():
        try:
            await _process_batch(db, client_id, platform, posts)
        except Exception as exc:
            logger.error(
                "metrics_poll batch error client=%s platform=%s: %s",
                client_id, platform, exc,
                exc_info=True,
            )
            sentry_sdk.capture_exception(exc)


async def _select_due_meta_posts(db, now: datetime) -> list[PublishedPost]:
    """Return Meta published_posts that are within the 90-day horizon and due for a poll.

    Uses a LEFT JOIN on post_metrics to get each post's latest captured_at without
    loading full history (AD-A2).
    """
    cutoff = now - timedelta(days=90)
    platform_list = ", ".join(f"'{p}'" for p in _META_PLATFORMS)

    result = await db.execute(
        text(
            f"""
            SELECT
                pp.id,
                pp.campaign_id,
                pp.client_id,
                pp.platform,
                pp.platform_post_id,
                pp.permalink,
                pp.published_at,
                pp.created_at,
                MAX(pm.captured_at) AS last_captured_at
            FROM published_posts pp
            LEFT JOIN post_metrics pm ON pm.published_post_id = pp.id
            WHERE pp.platform IN ({platform_list})
              AND pp.published_at >= :cutoff
            GROUP BY pp.id, pp.campaign_id, pp.client_id, pp.platform,
                     pp.platform_post_id, pp.permalink, pp.published_at, pp.created_at
            """
        ),
        {"cutoff": cutoff.replace(tzinfo=None)},
    )
    rows = result.mappings().all()

    due: list[PublishedPost] = []
    for row in rows:
        published_at = row["published_at"]
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)
        last_captured_at = row["last_captured_at"]
        if last_captured_at is not None and last_captured_at.tzinfo is None:
            last_captured_at = last_captured_at.replace(tzinfo=timezone.utc)

        if is_due(published_at, last_captured_at, now):
            post = PublishedPost(
                id=row["id"],
                campaign_id=row["campaign_id"],
                client_id=row["client_id"],
                platform=row["platform"],
                platform_post_id=row["platform_post_id"],
                permalink=row["permalink"],
                published_at=row["published_at"],
                created_at=row["created_at"],
            )
            due.append(post)
    return due


async def _process_batch(
    db,
    client_id: uuid.UUID,
    platform: str,
    posts: list[PublishedPost],
) -> None:
    """Resolve credentials for a client+platform pair and fetch+insert snapshots."""
    conn = await get_connection_for_platform(db, client_id, platform)
    if not conn:
        logger.warning(
            "metrics_poll: no %s connection for client=%s — skipping %d post(s)",
            platform, client_id, len(posts),
        )
        return

    creds_json = decrypt_credential(conn.encrypted_credentials)
    creds = json.loads(creds_json)

    snapshots = await meta_metrics.fetch(posts, creds, platform)
    if snapshots:
        await bulk_insert_snapshots(db, snapshots)
        await db.commit()

    logger.info(
        "metrics_poll: %d snapshot(s) inserted client=%s platform=%s",
        len(snapshots), client_id, platform,
    )

    # Small stagger between platforms to be polite to Meta's rate limits
    await asyncio.sleep(0.5)
