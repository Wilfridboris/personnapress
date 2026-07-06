import asyncio
import hashlib
import logging
from datetime import datetime, timedelta, timezone

import sentry_sdk
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection import async_session_factory
from app.db.repositories.models import (
    Campaign, Client, GenerationLog, Job, PlatformConnection, Subscription, User,
)
from app.integrations.email import send_deletion_warning_email

logger = logging.getLogger(__name__)
BATCH_LIMIT = 50


async def subscription_cleanup() -> None:
    """
    Daily APScheduler job. Two-phase cleanup:
    Phase 1: Find trial_expired users > 30 days → send warning email, set deletion_scheduled_at
    Phase 2: Find users with deletion_scheduled_at in the past → anonymize and delete
    """
    async with async_session_factory() as db:
        await _phase1_warn(db)
        await _phase2_delete(db)


async def _phase1_warn(db: AsyncSession) -> None:
    """Send warning emails for users whose trial expired > 30 days ago with no deletion date set."""
    cutoff_30d = datetime.now(timezone.utc) - timedelta(days=30)
    result = await db.execute(
        select(Subscription)
        .where(
            Subscription.status == "trial_expired",
            Subscription.deletion_scheduled_at.is_(None),
            Subscription.updated_at <= cutoff_30d.replace(tzinfo=None),
        )
        .limit(BATCH_LIMIT)
        .with_for_update(skip_locked=True)
    )
    subs = result.scalars().all()

    for sub in subs:
        try:
            user_result = await db.execute(
                select(User).where(User.id == sub.user_id)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                continue

            deletion_date = datetime.now(timezone.utc) + timedelta(days=7)
            # Cross-platform: avoids %-d (Linux) vs %#d (Windows) divergence
            deletion_date_str = f"{deletion_date.strftime('%B')} {deletion_date.day}, {deletion_date.year}"

            # Commit deletion date first — email is sent after. If email fails post-commit,
            # deletion_scheduled_at is already set so the next daily run won't re-warn.
            sub.deletion_scheduled_at = deletion_date.replace(tzinfo=None)
            await db.commit()

            await asyncio.to_thread(send_deletion_warning_email, user.email, deletion_date_str)
            logger.info("Deletion warning sent for user %s", str(sub.user_id))
        except Exception as exc:
            await db.rollback()
            sentry_sdk.capture_exception(exc)
            logger.error("Phase1 warning failed for subscription %s: %s", str(sub.id), exc)


async def _phase2_delete(db: AsyncSession) -> None:
    """Delete accounts where deletion_scheduled_at has passed."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    result = await db.execute(
        select(Subscription)
        .where(
            Subscription.status == "trial_expired",
            Subscription.deletion_scheduled_at.is_not(None),
            Subscription.deletion_scheduled_at <= now,
        )
        .limit(BATCH_LIMIT)
        .with_for_update(skip_locked=True)
    )
    subs = result.scalars().all()

    for sub in subs:
        try:
            user_id = sub.user_id
            await _delete_user_data(db, user_id)
            await _anonymize_user(db, user_id)
            await db.commit()
            user_id_str = str(user_id)
            sentry_sdk.capture_message(
                f"Account deleted (audit): user_id={user_id_str}",
                level="info",
            )
            logger.info("Account deleted for user %s", user_id_str)
        except Exception as exc:
            await db.rollback()
            sentry_sdk.capture_exception(exc)
            logger.error("Phase2 delete failed for subscription %s: %s", str(sub.id), exc)


async def _delete_user_data(db: AsyncSession, user_id) -> None:
    """Delete all data rows for the user except the users row itself."""
    # Delete order: generation_logs → jobs → campaigns → platform_connections → clients → subscriptions
    clients_result = await db.execute(
        select(Client.id).where(Client.user_id == user_id)
    )
    client_ids = [row[0] for row in clients_result.all()]

    if client_ids:
        campaigns_result = await db.execute(
            select(Campaign.id).where(Campaign.client_id.in_(client_ids))
        )
        campaign_ids = [row[0] for row in campaigns_result.all()]
        if campaign_ids:
            await db.execute(
                GenerationLog.__table__.delete().where(GenerationLog.campaign_id.in_(campaign_ids))
            )
            await db.execute(
                Job.__table__.delete().where(Job.campaign_id.in_(campaign_ids))
            )
        await db.execute(
            Campaign.__table__.delete().where(Campaign.client_id.in_(client_ids))
        )
        await db.execute(
            PlatformConnection.__table__.delete().where(PlatformConnection.client_id.in_(client_ids))
        )

    await db.execute(
        Client.__table__.delete().where(Client.user_id == user_id)
    )
    await db.execute(
        GenerationLog.__table__.delete().where(GenerationLog.user_id == user_id)
    )
    await db.execute(
        Subscription.__table__.delete().where(Subscription.user_id == user_id)
    )
    await db.flush()


async def _anonymize_user(db: AsyncSession, user_id) -> None:
    """Anonymize the users row: hash email, clear password and OAuth identifiers."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        logger.error("_anonymize_user: no User row found for user_id=%s — data deleted but user not anonymized", str(user_id))
        sentry_sdk.capture_message(f"_anonymize_user: missing user row for user_id={user_id}", level="error")
        return
    hashed_email = "deleted_" + hashlib.sha256(user.email.encode()).hexdigest()[:16] + "@anonymized.invalid"
    user.email = hashed_email
    user.hashed_password = None
    user.google_sub = None
    user.stripe_customer_id = None
    await db.flush()
