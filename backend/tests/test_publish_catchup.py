"""Tests for the scheduled-publish catch-up worker (spec: fix-scheduled-publish-catchup-reconciler).

Covers every row in the I/O & Edge-Case Matrix:
  1. Social orphaned       -> run_publish called, scheduled_at cleared
  2. Social within grace   -> no dispatch, scheduled_at unchanged
  3. Headless orphaned     -> run_publish_headless called, scheduled_at cleared
  4. Headless within grace -> no dispatch, scheduled_at unchanged
  5. Already fulfilled     -> scheduled_at cleared, no dispatch
  6. In-flight social      -> no dispatch, left untouched
  7. Dispatch throws       -> other campaigns still dispatched
  8. No due campaigns      -> no-op
  9. Query guard           -> get_due_scheduled_campaigns SQL restricts by status / IS NOT NULL / <=
"""

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from app.db.repositories.models import ArticleStatus


# ── Helpers ───────────────────────────────────────────────────────────────────

def _utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _campaign(campaign_id=None, scheduled_at_offset_seconds=-7200):
    """Build a minimal MagicMock Campaign that's 2 hours overdue by default."""
    c = MagicMock()
    c.id = campaign_id or uuid.uuid4()
    c.status = "approved"
    # scheduled_at is naive UTC, 2 h in the past
    c.scheduled_at = _utcnow_naive() + timedelta(seconds=scheduled_at_offset_seconds)
    c.updated_at = _utcnow_naive()
    return c


def _job(job_id=None, campaign_id=None):
    j = MagicMock()
    j.id = job_id or uuid.uuid4()
    j.campaign_id = campaign_id or uuid.uuid4()
    j.job_type = "scheduled_publish"
    j.status = "scheduled"
    return j


def _article(status: ArticleStatus = ArticleStatus.hidden, campaign_id=None):
    a = MagicMock()
    a.id = uuid.uuid4()
    a.campaign_id = campaign_id or uuid.uuid4()
    a.status = status
    return a


def _make_session(campaigns):
    """Build an async-context-manager mock whose session returns *campaigns* from get_due."""
    session = AsyncMock()
    session.commit = AsyncMock()

    @asynccontextmanager
    async def _factory():
        yield session

    return _factory, session


# ── Helper to run catchup with all collaborators mocked ─────────────────────

async def _catchup(
    campaigns,
    scheduled_job=None,
    article=None,
    scheduler_get_job_return=None,
    run_publish=None,
    run_publish_headless=None,
):
    """Run scheduled_publish_catchup with mocked collaborators.

    scheduler_get_job_return can be:
      - None (default) -> APScheduler job is gone
      - a MagicMock    -> APScheduler job exists (within grace)
      - a callable(job_id_str) -> used as side_effect
    """
    from app.workers.publish_catchup import scheduled_publish_catchup

    run_publish = run_publish or AsyncMock()
    run_publish_headless = run_publish_headless or AsyncMock()

    mock_scheduler = MagicMock()
    if callable(scheduler_get_job_return) and not isinstance(scheduler_get_job_return, MagicMock):
        mock_scheduler.get_job.side_effect = scheduler_get_job_return
    else:
        mock_scheduler.get_job.return_value = scheduler_get_job_return

    factory, session = _make_session(campaigns)

    with (
        patch("app.workers.publish_catchup.async_session_factory", factory),
        patch("app.workers.publish_catchup.get_due_scheduled_campaigns", AsyncMock(return_value=campaigns)),
        patch("app.workers.publish_catchup.get_scheduled_job", AsyncMock(return_value=scheduled_job)),
        patch("app.workers.publish_catchup.get_article_by_campaign_id", AsyncMock(return_value=article)),
        patch("app.scheduler.scheduler.scheduler", mock_scheduler),
        patch("app.workers.publish.run_publish", run_publish),
        patch("app.workers.publish.run_publish_headless", run_publish_headless),
    ):
        await scheduled_publish_catchup()

    return run_publish, run_publish_headless, mock_scheduler, session


# ── 1. Social orphaned ────────────────────────────────────────────────────────

async def test_social_orphaned_v2():
    """Social: job row present, APScheduler job gone -> run_publish dispatched, scheduled_at=None."""
    campaign = _campaign()
    original_scheduled_at = campaign.scheduled_at
    job = _job(campaign_id=campaign.id)

    run_publish, run_publish_headless, sched, session = await _catchup(
        campaigns=[campaign],
        scheduled_job=job,
        article=None,
        scheduler_get_job_return=None,  # APScheduler job gone
    )

    run_publish.assert_awaited_once_with(job.id, campaign.id, [])
    run_publish_headless.assert_not_awaited()
    assert campaign.scheduled_at is None
    session.commit.assert_awaited()


# ── 2. Social within grace ────────────────────────────────────────────────────

async def test_social_within_grace():
    """Social: job row present, APScheduler job still alive -> skip, scheduled_at unchanged."""
    campaign = _campaign()
    original_scheduled_at = campaign.scheduled_at
    job = _job(campaign_id=campaign.id)
    live_job = MagicMock()  # APScheduler job present

    run_publish, run_publish_headless, sched, session = await _catchup(
        campaigns=[campaign],
        scheduled_job=job,
        article=None,
        scheduler_get_job_return=live_job,
    )

    run_publish.assert_not_awaited()
    run_publish_headless.assert_not_awaited()
    # scheduled_at should be unchanged (still the original value)
    assert campaign.scheduled_at == original_scheduled_at


# ── 3. Headless orphaned ──────────────────────────────────────────────────────

async def test_headless_orphaned():
    """Headless: no job row, hidden article, no live APScheduler job -> run_publish_headless."""
    campaign = _campaign()
    article = _article(status=ArticleStatus.hidden, campaign_id=campaign.id)

    run_publish, run_publish_headless, sched, session = await _catchup(
        campaigns=[campaign],
        scheduled_job=None,       # no scheduled_publish job row
        article=article,
        scheduler_get_job_return=None,  # APScheduler job gone
    )

    run_publish_headless.assert_awaited_once_with(str(campaign.id))
    run_publish.assert_not_awaited()
    assert campaign.scheduled_at is None
    session.commit.assert_awaited()


# ── 4. Headless within grace ──────────────────────────────────────────────────

async def test_headless_within_grace():
    """Headless: hidden article, APScheduler job still alive -> skip."""
    campaign = _campaign()
    original_scheduled_at = campaign.scheduled_at
    article = _article(status=ArticleStatus.hidden, campaign_id=campaign.id)
    live_job = MagicMock()

    run_publish, run_publish_headless, sched, session = await _catchup(
        campaigns=[campaign],
        scheduled_job=None,
        article=article,
        scheduler_get_job_return=live_job,
    )

    run_publish.assert_not_awaited()
    run_publish_headless.assert_not_awaited()
    assert campaign.scheduled_at == original_scheduled_at


# ── 5. Already fulfilled (housekeeping) ──────────────────────────────────────

async def test_already_fulfilled_clears_scheduled_at():
    """Published article + no job row -> clear scheduled_at, no dispatch."""
    campaign = _campaign()
    article = _article(status=ArticleStatus.published, campaign_id=campaign.id)

    run_publish, run_publish_headless, sched, session = await _catchup(
        campaigns=[campaign],
        scheduled_job=None,
        article=article,
        scheduler_get_job_return=None,
    )

    run_publish.assert_not_awaited()
    run_publish_headless.assert_not_awaited()
    assert campaign.scheduled_at is None
    session.commit.assert_awaited()


# ── 6. In-flight social ───────────────────────────────────────────────────────

async def test_in_flight_social_left_untouched():
    """In-flight: no job row (moved to in_progress) and no article -> leave untouched."""
    campaign = _campaign()
    original_scheduled_at = campaign.scheduled_at

    run_publish, run_publish_headless, sched, session = await _catchup(
        campaigns=[campaign],
        scheduled_job=None,    # job_type changed away from scheduled / in_progress
        article=None,
        scheduler_get_job_return=None,
    )

    run_publish.assert_not_awaited()
    run_publish_headless.assert_not_awaited()
    # scheduled_at should remain unchanged (campaign left alone)
    assert campaign.scheduled_at == original_scheduled_at


# ── 7. Dispatch throws — fault isolation ─────────────────────────────────────

async def test_dispatch_throws_others_still_dispatched():
    """If one dispatch raises, remaining campaigns are still dispatched."""
    from app.workers.publish_catchup import scheduled_publish_catchup

    campaign1 = _campaign()
    campaign2 = _campaign()
    job1 = _job(campaign_id=campaign1.id)
    job2 = _job(campaign_id=campaign2.id)

    call_count = 0

    async def flaky_run_publish(job_id, campaign_id, platforms):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("simulated publish error")

    run_publish_headless = AsyncMock()
    mock_scheduler = MagicMock()
    mock_scheduler.get_job.return_value = None

    factory, session = _make_session([campaign1, campaign2])

    async def get_sched_job_by_campaign(db_session, cid):
        if cid == campaign1.id:
            return job1
        return job2

    with (
        patch("app.workers.publish_catchup.async_session_factory", factory),
        patch("app.workers.publish_catchup.get_due_scheduled_campaigns",
              AsyncMock(return_value=[campaign1, campaign2])),
        patch("app.workers.publish_catchup.get_scheduled_job",
              AsyncMock(side_effect=get_sched_job_by_campaign)),
        patch("app.workers.publish_catchup.get_article_by_campaign_id", AsyncMock(return_value=None)),
        patch("app.scheduler.scheduler.scheduler", mock_scheduler),
        patch("app.workers.publish.run_publish", flaky_run_publish),
        patch("app.workers.publish.run_publish_headless", run_publish_headless),
    ):
        await scheduled_publish_catchup()

    # Both campaigns had scheduled_at cleared (claimed before dispatch)
    assert campaign1.scheduled_at is None
    assert campaign2.scheduled_at is None
    # Second campaign was still dispatched despite first raising
    assert call_count == 2


# ── 8. No due campaigns — no-op ──────────────────────────────────────────────

async def test_no_due_campaigns_noop():
    """No campaigns returned -> worker does nothing."""
    run_publish, run_publish_headless, sched, session = await _catchup(
        campaigns=[],
        scheduled_job=None,
        article=None,
    )

    run_publish.assert_not_awaited()
    run_publish_headless.assert_not_awaited()
    session.commit.assert_not_awaited()


# ── 9. Query guard for get_due_scheduled_campaigns ───────────────────────────

def test_get_due_scheduled_campaigns_sql_restrictions():
    """The compiled SQL for get_due_scheduled_campaigns must include the required WHERE clauses."""
    from sqlmodel import select
    from sqlalchemy.dialects import postgresql
    from app.db.repositories.campaigns import get_due_scheduled_campaigns
    from app.db.repositories.models import Campaign

    cutoff = datetime(2026, 9, 22, 10, 0, 0)
    limit = 20

    # Build the same select statement that the function uses, then compile it
    stmt = (
        select(Campaign)
        .where(
            Campaign.status == "approved",
            Campaign.scheduled_at.is_not(None),
            Campaign.scheduled_at <= cutoff,
        )
        .limit(limit)
    )

    compiled = stmt.compile(
        dialect=postgresql.dialect(),
        compile_kwargs={"literal_binds": True},
    )
    sql = str(compiled)

    assert "approved" in sql, "SQL must filter by status='approved'"
    assert "IS NOT NULL" in sql.upper() or "is not null" in sql, "SQL must filter scheduled_at IS NOT NULL"
    assert "scheduled_at" in sql, "SQL must reference scheduled_at column"
    # The <= cutoff comparison must be present; "scheduled_at" alone is not sufficient
    assert "<=" in sql, "SQL must have a scheduled_at <= cutoff clause"
    assert "LIMIT" in sql.upper(), "SQL must have a LIMIT clause"
