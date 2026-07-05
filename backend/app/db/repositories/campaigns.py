import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.repositories.models import Campaign, utcnow


async def create_campaign(
    session: AsyncSession,
    client_id: uuid.UUID,
    brain_dump: str,
) -> Campaign:
    campaign = Campaign(client_id=client_id, brain_dump=brain_dump, status="pending_approval")
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


async def update_campaign_status(
    session: AsyncSession,
    campaign_id: uuid.UUID,
    status: str,
) -> Optional[Campaign]:
    campaign = await get_campaign(session, campaign_id)
    if not campaign:
        return None
    campaign.status = status
    campaign.updated_at = utcnow()
    await session.flush()
    await session.refresh(campaign)
    return campaign


async def update_campaign_scheduled_at(
    session: AsyncSession,
    campaign_id: uuid.UUID,
    scheduled_at: Optional[datetime],
) -> Optional[Campaign]:
    campaign = await get_campaign(session, campaign_id)
    if not campaign:
        return None
    campaign.scheduled_at = scheduled_at
    campaign.updated_at = utcnow()
    await session.flush()
    await session.refresh(campaign)
    return campaign


async def update_campaign_content(
    session: AsyncSession,
    campaign_id: uuid.UUID,
    blog_html: str,
    voice_score: dict,
    x_post: str,
    linkedin_post: str,
) -> Optional[Campaign]:
    """Atomically update all text generation fields on a campaign."""
    campaign = await get_campaign(session, campaign_id)
    if not campaign:
        return None
    campaign.blog_html = blog_html
    campaign.voice_score = voice_score
    campaign.x_post = x_post
    campaign.linkedin_post = linkedin_post
    await session.flush()
    await session.refresh(campaign)
    return campaign
