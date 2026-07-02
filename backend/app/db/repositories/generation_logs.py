import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.models import GenerationLog


async def create_generation_log(
    session: AsyncSession,
    user_id: uuid.UUID,
    campaign_id: uuid.UUID,
    gemini_tokens: Optional[int] = None,
    replicate_count: Optional[int] = None,
) -> GenerationLog:
    log = GenerationLog(
        user_id=user_id,
        campaign_id=campaign_id,
        gemini_tokens=gemini_tokens,
        replicate_count=replicate_count,
    )
    session.add(log)
    await session.flush()
    await session.refresh(log)
    return log
