from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.workers.analytics import metrics_poll
from app.workers.cleanup import subscription_cleanup
from app.workers.reengagement import trial_reengagement_check


def create_scheduler() -> AsyncIOScheduler:
    sync_db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    jobstores = {"default": SQLAlchemyJobStore(url=sync_db_url)}
    scheduler = AsyncIOScheduler(jobstores=jobstores, timezone="UTC")

    # Daily cleanup job — runs at 02:00 UTC every day.
    # replace_existing=True ensures a stale job row from a previous deployment is replaced.
    # misfire_grace_time=3600 allows the job to run up to 1 hour late after server restart.
    scheduler.add_job(
        subscription_cleanup,
        trigger="cron",
        hour=2,
        minute=0,
        id="subscription_cleanup",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Daily re-engagement job — runs at 09:00 UTC every day.
    scheduler.add_job(
        trial_reengagement_check,
        trigger="cron",
        hour=9,
        minute=0,
        id="trial_reengagement_check",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    if settings.ANALYTICS_ENABLED:
        # Meta metrics harvest — runs every 30 minutes.
        # Cadence logic inside the worker decides which posts are actually due;
        # the scheduler just ensures a frequent enough trigger window.
        scheduler.add_job(
            metrics_poll,
            trigger="interval",
            minutes=30,
            id="metrics_poll",
            replace_existing=True,
            misfire_grace_time=600,
        )

    return scheduler


scheduler = create_scheduler()
