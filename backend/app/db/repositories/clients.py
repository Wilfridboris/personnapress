import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.repositories.models import Client


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
