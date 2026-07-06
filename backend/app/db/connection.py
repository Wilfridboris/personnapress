from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,   # discard dead connections before use
    pool_recycle=1800,    # recycle connections every 30 min (Supabase pooler idle timeout)
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
async_session_factory = AsyncSessionLocal  # for workers running outside the HTTP request lifecycle


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


from contextlib import asynccontextmanager


@asynccontextmanager
async def get_session_context():
    """Async context manager for DB sessions used in BackgroundTasks."""
    async with AsyncSessionLocal() as session:
        yield session


async def create_db_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
