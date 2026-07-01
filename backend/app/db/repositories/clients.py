import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, case, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.models import Campaign, Client, GenerationLog, Job, PlatformConnection


async def create_client(
    session: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    website_url: Optional[str],
) -> Client:
    client = Client(user_id=user_id, name=name, website_url=website_url)
    session.add(client)
    await session.flush()
    await session.refresh(client)
    return client


async def get_client(
    session: AsyncSession,
    client_id: uuid.UUID,
) -> Optional[Client]:
    result = await session.execute(select(Client).where(Client.id == client_id))
    return result.scalar_one_or_none()


async def get_clients_by_user(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> list:
    stmt = (
        select(
            Client,
            func.count(Campaign.id).label("campaign_count"),
            func.max(
                case(
                    (Job.status.in_(["pending", "in_progress"]), 1),
                    else_=0,
                )
            ).label("has_active_ingestion"),
        )
        .outerjoin(Campaign, Campaign.client_id == Client.id)
        .outerjoin(
            Job,
            and_(Job.client_id == Client.id, Job.job_type == "ingestion"),
        )
        .where(Client.user_id == user_id)
        .group_by(Client.id)
        .order_by(Client.name)
    )
    result = await session.execute(stmt)
    return result.all()


async def get_campaign_count(
    session: AsyncSession,
    client_id: uuid.UUID,
) -> int:
    result = await session.execute(
        select(func.count()).select_from(Campaign).where(Campaign.client_id == client_id)
    )
    return result.scalar_one()


async def update_client(
    session: AsyncSession,
    client_id: uuid.UUID,
    **fields: object,
) -> Optional[Client]:
    client = await get_client(session, client_id)
    if not client:
        return None
    for key, value in fields.items():
        setattr(client, key, value)
    client.updated_at = datetime.now(timezone.utc)
    session.add(client)
    await session.flush()
    await session.refresh(client)
    return client


async def delete_client(
    session: AsyncSession,
    client_id: uuid.UUID,
) -> None:
    # Collect campaign IDs for this client to handle grandchild dependencies
    campaign_ids_result = await session.execute(
        select(Campaign.id).where(Campaign.client_id == client_id)
    )
    campaign_ids = [row[0] for row in campaign_ids_result.fetchall()]

    # Delete generation_logs referencing those campaigns
    if campaign_ids:
        await session.execute(
            delete(GenerationLog).where(GenerationLog.campaign_id.in_(campaign_ids))
        )
        # Nullify jobs that reference those campaigns (jobs may also reference client directly)
        jobs_for_campaigns_result = await session.execute(
            select(Job).where(Job.campaign_id.in_(campaign_ids))
        )
        for job in jobs_for_campaigns_result.scalars().all():
            job.campaign_id = None
            session.add(job)
        await session.flush()

    # Delete jobs where client_id = client_id
    await session.execute(delete(Job).where(Job.client_id == client_id))

    # Delete platform_connections
    await session.execute(
        delete(PlatformConnection).where(PlatformConnection.client_id == client_id)
    )

    # Delete campaigns
    await session.execute(delete(Campaign).where(Campaign.client_id == client_id))

    # Delete the client
    await session.execute(delete(Client).where(Client.id == client_id))
