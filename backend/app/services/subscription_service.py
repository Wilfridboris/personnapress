import logging
import uuid
from datetime import datetime, timezone

import stripe as stripe_sdk
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlmodel import select

from app.core.config import settings
from app.core.constants import PLAN_LIMITS, UNLIMITED, get_stripe_price_to_tier
from app.db.repositories.models import Campaign, Client, GenerationLog, Subscription, User
from app.schemas.subscription import PlanLimits, SubscriptionResponse

logger = logging.getLogger(__name__)

# Ensure stripe_client initializes the SDK key
import app.integrations.stripe_client  # noqa: F401


async def check_and_expire_trial(user_id: uuid.UUID, db: AsyncSession) -> str | None:
    """
    Called on every authenticated request. If status='trialing' and billing_cycle_end
    has passed, atomically updates status to 'trial_expired'. Returns the effective status.
    """
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id).with_for_update()
    )
    sub = result.scalars().first()
    if sub is None:
        return None
    if (
        sub.status == "trialing"
        and datetime.now(timezone.utc) > sub.billing_cycle_end.replace(tzinfo=timezone.utc)
    ):
        sub.status = "trial_expired"
        sub.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()
    return sub.status


async def check_trial_not_expired(user_id: uuid.UUID, db: AsyncSession, action: str = "perform this action") -> None:
    """
    Raises HTTP 403 if user's subscription status is 'trial_expired'.
    Calls check_and_expire_trial first so stale 'trialing' rows are transitioned atomically
    before the gate check — prevents bypass by users who never hit /subscriptions/status.
    Call this BEFORE check_client_limit / check_campaign_limit / check_image_limit.
    """
    status = await check_and_expire_trial(user_id, db)
    if status == "trial_expired":
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "code": "TRIAL_EXPIRED",
                    "message": f"Subscribe to {action}.",
                    "detail": {"status": "trial_expired"},
                }
            },
        )


async def check_client_limit(user_id: uuid.UUID, db: AsyncSession) -> None:
    # Lock subscription row to serialize concurrent create-client requests (TOCTOU guard).
    # If no subscription row exists, fall back to locking the user row.
    sub_result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id).with_for_update()
    )
    sub = sub_result.scalars().first()

    if sub is None:
        await db.execute(select(User).where(User.id == user_id).with_for_update())

    if sub and sub.status in ("canceled", "expired", "past_due"):
        plan_tier = "starter"
    else:
        plan_tier = sub.plan_tier if sub else "starter"

    limit = PLAN_LIMITS.get(plan_tier, PLAN_LIMITS["starter"])["clients"]

    count_result = await db.execute(
        select(func.count()).select_from(Client).where(Client.user_id == user_id)
    )
    current: int = count_result.scalar() or 0

    if current >= limit:
        if plan_tier == "agency":
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "CLIENT_LIMIT_REACHED",
                        "message": (
                            f"You've reached your {limit}-client limit on the Agency plan. "
                            "Contact us to increase your limit."
                        ),
                        "detail": {"current": current, "limit": limit, "plan": plan_tier},
                    }
                },
            )
        next_tier_map = {"starter": "growth", "growth": "agency"}
        next_tier = next_tier_map.get(plan_tier, "agency")
        next_limit = PLAN_LIMITS.get(next_tier, PLAN_LIMITS["agency"])["clients"]
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "CLIENT_LIMIT_REACHED",
                    "message": (
                        f"You've reached your {limit}-client limit on the {plan_tier.capitalize()} plan. "
                        f"Upgrade to {next_tier.capitalize()} for up to {next_limit} clients."
                    ),
                    "detail": {
                        "current": current,
                        "limit": limit,
                        "plan": plan_tier,
                        "next_tier": next_tier,
                        "next_limit": next_limit,
                    },
                }
            },
        )


async def check_campaign_limit(db: AsyncSession, user_id: uuid.UUID) -> None:
    sub_result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id).with_for_update()
    )
    sub = sub_result.scalars().first()

    if sub and sub.status in ("canceled", "expired", "past_due"):
        plan_tier = "starter"
    else:
        plan_tier = sub.plan_tier if sub else "starter"

    limit = PLAN_LIMITS.get(plan_tier, PLAN_LIMITS["starter"])["campaigns"]

    if sub:
        current: int = sub.campaigns_used
    else:
        await db.execute(select(User).where(User.id == user_id).with_for_update())
        count_result = await db.execute(
            select(func.count()).select_from(Campaign)
            .join(Client, Campaign.client_id == Client.id)
            .where(Client.user_id == user_id)
        )
        current = count_result.scalar() or 0

    if limit >= UNLIMITED:
        # Agency: no campaign cap; still increment counter so account screen stays accurate
        if sub:
            sub.campaigns_used = current + 1
            await db.flush()
        return

    if current >= limit:
        next_tier_map = {"starter": "growth", "growth": "agency"}
        next_tier = next_tier_map.get(plan_tier, "agency")
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "CAMPAIGN_LIMIT_EXCEEDED",
                    "message": (
                        f"You've reached your {limit}-campaign limit for this billing cycle. "
                        f"Upgrade to {next_tier.capitalize()} for more campaigns."
                    ),
                    "detail": {
                        "current": current,
                        "limit": limit,
                        "plan": plan_tier,
                        "next_tier": next_tier,
                    },
                }
            },
        )

    if sub:
        sub.campaigns_used = current + 1
        await db.flush()


async def check_image_limit(db: AsyncSession, user_id: uuid.UUID) -> None:
    sub_result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id).with_for_update()
    )
    sub = sub_result.scalars().first()

    if sub and sub.status in ("canceled", "expired", "past_due"):
        plan_tier = "starter"
    else:
        plan_tier = sub.plan_tier if sub else "starter"

    limit = PLAN_LIMITS.get(plan_tier, PLAN_LIMITS["starter"])["image_gens"]

    if sub:
        current: int = sub.image_gen_used
    else:
        await db.execute(select(User).where(User.id == user_id).with_for_update())
        count_result = await db.execute(
            select(func.coalesce(func.sum(GenerationLog.replicate_count), 0))
            .where(
                GenerationLog.user_id == user_id,
                GenerationLog.replicate_count.isnot(None),
            )
        )
        current = int(count_result.scalar() or 0)

    if current >= limit:
        next_tier_map = {"starter": "growth", "growth": "agency"}
        next_tier = next_tier_map.get(plan_tier, "agency")
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "IMAGE_LIMIT_EXCEEDED",
                    "message": (
                        f"You've reached your {limit}-image limit for this billing cycle. "
                        f"Upgrade to {next_tier.capitalize()} for more image generations."
                    ),
                    "detail": {
                        "current": current,
                        "limit": limit,
                        "plan": plan_tier,
                        "next_tier": next_tier,
                    },
                }
            },
        )

    if sub:
        sub.image_gen_used = current + 1
        await db.flush()


async def get_user_plan_info(user_id: uuid.UUID, db: AsyncSession) -> tuple[str, int]:
    result = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
    sub = result.scalar_one_or_none()

    if sub and sub.status in ("canceled", "expired", "past_due"):
        plan_tier = "starter"
    else:
        plan_tier = sub.plan_tier if sub else "starter"

    client_limit = PLAN_LIMITS.get(plan_tier, PLAN_LIMITS["starter"])["clients"]
    return plan_tier, client_limit


async def get_subscription(user_id: str, db: AsyncSession) -> SubscriptionResponse:
    result = await db.execute(select(Subscription).where(Subscription.user_id == uuid.UUID(user_id)))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "SUBSCRIPTION_NOT_FOUND", "message": "Subscription not found.", "detail": {}}},
        )
    limits = PLAN_LIMITS.get(sub.plan_tier, PLAN_LIMITS["starter"])
    return SubscriptionResponse(
        plan_tier=sub.plan_tier,
        status=sub.status,
        campaigns_used=sub.campaigns_used,
        clients_count=sub.clients_count,
        image_gen_used=sub.image_gen_used,
        billing_cycle_start=sub.billing_cycle_start,
        billing_cycle_end=sub.billing_cycle_end,
        plan_limits=PlanLimits(**limits),
    )


async def create_billing_portal_session(user_id: str, db: AsyncSession) -> str:
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "USER_NOT_FOUND", "message": "User not found.", "detail": {}}},
        )
    if not user.stripe_customer_id:
        customer = stripe_sdk.Customer.create(email=user.email, metadata={"user_id": user_id})
        user.stripe_customer_id = customer.id
        db.add(user)
        await db.commit()
    session = stripe_sdk.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=settings.APP_URL + "/account",
    )
    return session.url


async def handle_stripe_webhook(event: dict, db: AsyncSession) -> None:
    event_type = event.get("type")
    if event_type in ("customer.subscription.updated", "customer.subscription.created"):
        await _handle_subscription_updated(event["data"]["object"], db)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(event["data"]["object"], db)
    else:
        logger.info("Unhandled Stripe event type: %s", event_type)


async def _handle_subscription_updated(sub_obj: dict, db: AsyncSession) -> None:
    stripe_sub_id = sub_obj.get("id")
    result = await db.execute(select(Subscription).where(Subscription.stripe_sub_id == stripe_sub_id))
    sub = result.scalar_one_or_none()
    if not sub:
        logger.info("No subscription found for stripe_sub_id: %s", stripe_sub_id)
        return

    price_to_tier = get_stripe_price_to_tier()
    items = sub_obj.get("items", {}).get("data", [])
    if items:
        price_id = items[0].get("price", {}).get("id")
        if price_id and price_id in price_to_tier:
            sub.plan_tier = price_to_tier[price_id]

    sub.status = sub_obj.get("status", sub.status)
    if sub.status == "active":
        sub.deletion_scheduled_at = None  # cancel any pending deletion when user subscribes
    sub.billing_cycle_start = datetime.fromtimestamp(sub_obj["current_period_start"], tz=timezone.utc)
    sub.billing_cycle_end = datetime.fromtimestamp(sub_obj["current_period_end"], tz=timezone.utc)
    sub.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()


async def _handle_subscription_deleted(sub_obj: dict, db: AsyncSession) -> None:
    stripe_sub_id = sub_obj.get("id")
    result = await db.execute(select(Subscription).where(Subscription.stripe_sub_id == stripe_sub_id))
    sub = result.scalar_one_or_none()
    if not sub:
        logger.info("No subscription found for stripe_sub_id: %s", stripe_sub_id)
        return

    sub.status = "canceled"
    sub.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
