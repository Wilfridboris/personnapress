import asyncio
import logging
from datetime import datetime, timedelta, timezone

import sentry_sdk
from sqlalchemy import select

from app.db.connection import async_session_factory
from app.db.repositories.models import Campaign, Client, Subscription, User
from app.integrations.email import send_reengagement_email
from app.workers.cleanup import BATCH_LIMIT

logger = logging.getLogger(__name__)


async def trial_reengagement_check() -> None:
    """
    Daily APScheduler job. Finds trialing users with zero campaigns
    who signed up more than 3 days ago and haven't been emailed yet.
    """
    async with async_session_factory() as db:
        cutoff_3d = datetime.now(timezone.utc) - timedelta(days=3)

        # Subquery: user has at least one campaign across any client
        has_campaign = (
            select(Campaign.id)
            .join(Client, Campaign.client_id == Client.id)
            .where(Client.user_id == User.id)
            .exists()
        )

        result = await db.execute(
            select(User, Subscription)
            .join(Subscription, Subscription.user_id == User.id)
            .where(
                Subscription.status == "trialing",
                Subscription.reengagement_email_sent_at.is_(None),
                User.created_at < cutoff_3d.replace(tzinfo=None),
                ~has_campaign,
            )
            .limit(BATCH_LIMIT)
            .with_for_update(skip_locked=True)
        )
        rows = result.all()

        for user, sub in rows:
            try:
                # Set sent_at BEFORE sending so a Resend exception triggers rollback (AC8)
                sub.reengagement_email_sent_at = datetime.now(timezone.utc).replace(tzinfo=None)
                await db.flush()
                await asyncio.to_thread(send_reengagement_email, user.email, None)
                await db.commit()
                logger.info("Re-engagement email sent for user %s", str(user.id))
            except Exception as exc:
                await db.rollback()
                sentry_sdk.capture_exception(exc)
                logger.error("Re-engagement failed for user %s: %s", str(user.id), exc)
