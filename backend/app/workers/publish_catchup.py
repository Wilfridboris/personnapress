"""Scheduled catch-up worker for missed / orphaned publish jobs.

Two root causes for silent missed posts are addressed here:
  1. Deploy wipes the APScheduler job store (alembic drops apscheduler_jobs).
  2. Misfire beyond grace_time (server down > 1 h).

This worker runs every 5 minutes (and once at startup) and re-dispatches any
``approved`` campaign whose ``scheduled_at`` has passed but whose APScheduler
job is gone.
"""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

import sentry_sdk

from app.db.connection import async_session_factory
from app.db.repositories.articles import get_article_by_campaign_id
from app.db.repositories.campaigns import get_due_scheduled_campaigns
from app.db.repositories.jobs import get_scheduled_job
from app.db.repositories.models import ArticleStatus, utcnow

logger = logging.getLogger(__name__)

BATCH_LIMIT = 20


async def scheduled_publish_catchup() -> None:
    """Find and recover orphaned scheduled publishes.

    Never raises — all per-campaign failures are caught and logged so the
    APScheduler job store never marks the interval job as failed.
    """
    # Lazy import to avoid a circular dependency (scheduler -> worker -> scheduler).
    from app.scheduler.scheduler import scheduler
    from app.workers.publish import run_publish, run_publish_headless

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=60)

    try:
        async with async_session_factory() as db:
            campaigns = await get_due_scheduled_campaigns(db, cutoff, BATCH_LIMIT)

            if not campaigns:
                return

            # Classification pass — decide what to do with each campaign before
            # committing so the single commit is as small as possible.
            to_dispatch: list[tuple[str, UUID | None, UUID, float]] = []
            # Each entry: (kind, job_id_or_None, campaign_id, lateness_seconds)

            for campaign in campaigns:
                try:
                    now_naive = utcnow()
                    lateness = (now_naive - campaign.scheduled_at).total_seconds()

                    # ── Social branch ───────────────────────────────────────────
                    sched_job = await get_scheduled_job(db, campaign.id)
                    if sched_job is not None:
                        # A scheduled_publish job row exists → social schedule.
                        live = scheduler.get_job(str(sched_job.id))
                        if live is not None:
                            # Still within APScheduler grace window — leave it alone.
                            logger.debug(
                                "catchup: social campaign=%s still has live APScheduler job — skipping",
                                campaign.id,
                            )
                            continue
                        # Job row present but APScheduler entry gone → orphaned.
                        campaign.scheduled_at = None
                        campaign.updated_at = now_naive
                        to_dispatch.append(("social", sched_job.id, campaign.id, lateness))
                        continue

                    # ── Headless branch ─────────────────────────────────────────
                    article = await get_article_by_campaign_id(db, campaign.id)
                    if article is not None and article.status == ArticleStatus.hidden:
                        live = scheduler.get_job(f"headless_{campaign.id}")
                        if live is not None:
                            # Still within APScheduler grace window — leave it alone.
                            logger.debug(
                                "catchup: headless campaign=%s still has live APScheduler job — skipping",
                                campaign.id,
                            )
                            continue
                        # Hidden article but no live APScheduler job → orphaned.
                        campaign.scheduled_at = None
                        campaign.updated_at = now_naive
                        to_dispatch.append(("headless", None, campaign.id, lateness))
                        continue

                    # ── Already fulfilled ────────────────────────────────────────
                    if article is not None and article.status == ArticleStatus.published:
                        # Headless campaign that already published; clear scheduled_at
                        # so it stops being re-scanned (housekeeping).
                        campaign.scheduled_at = None
                        campaign.updated_at = now_naive
                        logger.info(
                            "catchup: campaign=%s article already published — clearing scheduled_at",
                            campaign.id,
                        )
                        continue

                    # ── In-flight / unknown ──────────────────────────────────────
                    logger.info(
                        "catchup: campaign=%s has no scheduled job, no hidden/published article "
                        "and no live APScheduler job — leaving untouched (possibly in-flight)",
                        campaign.id,
                    )

                except Exception as exc:
                    logger.error(
                        "catchup: classification failed for campaign=%s: %s",
                        campaign.id,
                        exc,
                        exc_info=True,
                    )
                    sentry_sdk.capture_message(
                        f"catchup: classification failed for campaign={campaign.id}: {exc}",
                        level="error",
                    )

            # Single commit — claims all campaigns atomically.
            await db.commit()

        # ── Dispatch phase (outside the DB session) ──────────────────────────
        recovered: list[tuple[str, UUID | None, UUID, float]] = []
        for kind, job_id, campaign_id, lateness in to_dispatch:
            try:
                if kind == "social":
                    await run_publish(job_id, campaign_id, [])
                else:
                    await run_publish_headless(str(campaign_id))
                recovered.append((kind, job_id, campaign_id, lateness))
            except Exception as exc:
                msg = (
                    f"catchup: dispatch failed for {kind} campaign={campaign_id} "
                    f"job={job_id}: {exc}"
                )
                logger.error(msg, exc_info=True)
                sentry_sdk.capture_message(msg, level="error")

        if recovered:
            details = "; ".join(
                f"{kind} campaign={cid} late={lateness:.0f}s"
                for kind, _jid, cid, lateness in recovered
            )
            summary = f"catchup: recovered {len(recovered)} post(s) — {details}"
            logger.warning(summary)
            sentry_sdk.capture_message(summary, level="warning")

    except Exception as exc:
        logger.error("catchup: unexpected error in scheduled_publish_catchup: %s", exc, exc_info=True)
        sentry_sdk.capture_message(
            f"catchup: unexpected error in scheduled_publish_catchup: {exc}",
            level="error",
        )
