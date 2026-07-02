import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.repositories.models import Campaign


async def create_campaign(
    session: AsyncSession,
    client_id: uuid.UUID,
    brain_dump: str,
) -> Campaign:
    campaign = Campaign(client_id=client_id, brain_dump=brain_dump)
    session.add(campaign)
    await session.flush()
    await session.refresh(campaign)
    return campaign


async def get_campaign(
    session: AsyncSession,
    campaign_id: uuid.UUID,
) -> Optional[Campaign]:
    result = await session.execute(select(Campaign).where(Campaign.id == campaign_id))
    return result.scalar_one_or_none()
