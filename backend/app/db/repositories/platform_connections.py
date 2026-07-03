import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.models import PlatformConnection, utcnow


async def get_connections_for_client(
    db: AsyncSession, client_id: uuid.UUID
) -> list[PlatformConnection]:
    result = await db.execute(
        select(PlatformConnection).where(PlatformConnection.client_id == client_id)
    )
    return list(result.scalars().all())


async def get_connection(
    db: AsyncSession, client_id: uuid.UUID, platform: str
) -> PlatformConnection | None:
    result = await db.execute(
        select(PlatformConnection).where(
            PlatformConnection.client_id == client_id,
            PlatformConnection.platform == platform,
        )
    )
    return result.scalar_one_or_none()


async def upsert_connection(
    db: AsyncSession,
    client_id: uuid.UUID,
    platform: str,
    encrypted_credentials: str,
) -> PlatformConnection:
    existing = await get_connection(db, client_id, platform)
    if existing:
        existing.encrypted_credentials = encrypted_credentials
        existing.updated_at = utcnow()
        db.add(existing)
        await db.commit()
        await db.refresh(existing)
        return existing
    connection = PlatformConnection(
        client_id=client_id,
        platform=platform,
        encrypted_credentials=encrypted_credentials,
    )
    db.add(connection)
    await db.commit()
    await db.refresh(connection)
    return connection


async def delete_connection(
    db: AsyncSession, client_id: uuid.UUID, platform: str
) -> bool:
    result = await db.execute(
        delete(PlatformConnection).where(
            PlatformConnection.client_id == client_id,
            PlatformConnection.platform == platform,
        )
    )
    await db.commit()
    return result.rowcount > 0
