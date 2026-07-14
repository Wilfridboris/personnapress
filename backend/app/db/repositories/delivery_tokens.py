"""DeliveryToken repository — plain async functions over AsyncSession."""

import hashlib
import hmac
import secrets
import uuid
from datetime import timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.models import DeliveryToken, utcnow

_TOKEN_PREFIX = "ppd_"
_TOUCH_INTERVAL_SECONDS = 60


def generate_raw_token() -> str:
    return _TOKEN_PREFIX + secrets.token_urlsafe(32)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def verify_token(raw: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_token(raw), stored_hash)


async def create_delivery_token(
    session: AsyncSession, client_id: uuid.UUID, name: str
) -> tuple[DeliveryToken, str]:
    """Create a new delivery token. Returns (record, raw_token). Raw token shown once."""
    raw = generate_raw_token()
    token = DeliveryToken(
        client_id=client_id,
        name=name,
        token_prefix=raw[:8],
        token_hash=hash_token(raw),
    )
    session.add(token)
    await session.flush()
    await session.refresh(token)
    return token, raw


async def list_delivery_tokens(
    session: AsyncSession, client_id: uuid.UUID
) -> list[DeliveryToken]:
    result = await session.execute(
        select(DeliveryToken)
        .where(DeliveryToken.client_id == client_id)
        .order_by(DeliveryToken.created_at.desc())
    )
    return list(result.scalars().all())


async def get_delivery_token(
    session: AsyncSession, token_id: uuid.UUID
) -> Optional[DeliveryToken]:
    result = await session.execute(
        select(DeliveryToken).where(DeliveryToken.id == token_id)
    )
    return result.scalar_one_or_none()


async def get_active_token_by_prefix(
    session: AsyncSession, prefix: str
) -> Optional[DeliveryToken]:
    """Fetch the active (non-revoked) token matching the given prefix for hash verification."""
    result = await session.execute(
        select(DeliveryToken).where(
            DeliveryToken.token_prefix == prefix,
            DeliveryToken.revoked_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def revoke_delivery_token(
    session: AsyncSession, token: DeliveryToken
) -> DeliveryToken:
    if token.revoked_at is not None:
        return token
    token.revoked_at = utcnow()
    session.add(token)
    await session.flush()
    return token


async def touch_last_used(
    session: AsyncSession, token: DeliveryToken
) -> None:
    """Update last_used_at at most once per minute per token."""
    now = utcnow()
    if token.last_used_at is not None:
        delta = now - token.last_used_at
        if delta < timedelta(seconds=_TOUCH_INTERVAL_SECONDS):
            return
    token.last_used_at = now
    session.add(token)
    await session.flush()
