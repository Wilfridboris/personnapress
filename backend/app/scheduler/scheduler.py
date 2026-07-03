from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings


def create_scheduler() -> AsyncIOScheduler:
    sync_db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    jobstores = {"default": SQLAlchemyJobStore(url=sync_db_url)}
    return AsyncIOScheduler(jobstores=jobstores, timezone="UTC")


scheduler = create_scheduler()
