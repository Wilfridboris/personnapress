"""Unit tests for subscription_service.py."""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.constants import PLAN_LIMITS, UNLIMITED
from app.services.subscription_service import (
    check_and_expire_trial,
    check_campaign_limit,
    check_image_limit_batch,
    check_roadmap_limit,
    check_trial_not_expired,
    create_checkout_session,
    handle_stripe_webhook,
)


def _make_sub(stripe_sub_id: str = "sub_123", status: str = "trialing"):
    m = MagicMock()
    m.stripe_sub_id = stripe_sub_id
    m.status = status
    m.plan_tier = "starter"
    m.billing_cycle_start = None
    m.billing_cycle_end = None
    m.updated_at = None
    return m


def _db_with_sub(sub):
    db = AsyncMock()
    r = MagicMock()
    r.scalar_one_or_none.return_value = sub
    db.execute = AsyncMock(return_value=r)
    return db


def _make_event(event_type: str, sub_id: str = "sub_123", status: str = "active"):
    now_ts = int(datetime(2026, 7, 6, tzinfo=timezone.utc).timestamp())
    return {
        "type": event_type,
        "data": {
            "object": {
                "id": sub_id,
                "status": status,
                "items": {"data": []},
                "current_period_start": now_ts,
                "current_period_end": now_ts + 30 * 86400,
            }
        },
    }


async def test_handle_subscription_created_sets_active():
    sub = _make_sub(status="trialing")
    db = _db_with_sub(sub)

    event = _make_event("customer.subscription.created", status="active")
    await handle_stripe_webhook(event, db)

    assert sub.status == "active"
    db.commit.assert_awaited_once()


async def test_handle_subscription_updated_sets_active():
    sub = _make_sub(status="trialing")
    db = _db_with_sub(sub)

    event = _make_event("customer.subscription.updated", status="active")
    await handle_stripe_webhook(event, db)

    assert sub.status == "active"
    db.commit.assert_awaited_once()


async def test_handle_subscription_created_no_sub_row_is_noop():
    db = AsyncMock()
    r = MagicMock()
    r.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=r)

    event = _make_event("customer.subscription.created", sub_id="sub_unknown")
    await handle_stripe_webhook(event, db)

    db.commit.assert_not_awaited()


async def test_unhandled_event_type_does_not_raise():
    db = AsyncMock()
    event = {"type": "payment_intent.succeeded", "data": {"object": {}}}
    await handle_stripe_webhook(event, db)
    db.commit.assert_not_awaited()


# ---------------------------------------------------------------------------
# check_and_expire_trial
# ---------------------------------------------------------------------------

def _make_sub_for_expiry(status: str, billing_cycle_end: datetime):
    m = MagicMock()
    m.status = status
    m.billing_cycle_end = billing_cycle_end.replace(tzinfo=None)  # stored naive
    m.updated_at = None
    return m


def _db_with_expiry_sub(sub):
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = sub
    db.execute = AsyncMock(return_value=result)
    return db


async def test_check_and_expire_trial_updates_status():
    past_end = datetime.now(timezone.utc) - timedelta(days=1)
    sub = _make_sub_for_expiry("trialing", past_end)
    db = _db_with_expiry_sub(sub)

    status = await check_and_expire_trial(uuid.uuid4(), db)

    assert sub.status == "trial_expired"
    assert status == "trial_expired"
    db.commit.assert_awaited_once()


async def test_check_and_expire_trial_no_op_when_active():
    future_end = datetime.now(timezone.utc) + timedelta(days=10)
    sub = _make_sub_for_expiry("active", future_end)
    db = _db_with_expiry_sub(sub)

    status = await check_and_expire_trial(uuid.uuid4(), db)

    assert sub.status == "active"
    assert status == "active"
    db.commit.assert_not_awaited()


async def test_check_and_expire_trial_no_op_when_trialing_not_yet_expired():
    future_end = datetime.now(timezone.utc) + timedelta(days=3)
    sub = _make_sub_for_expiry("trialing", future_end)
    db = _db_with_expiry_sub(sub)

    status = await check_and_expire_trial(uuid.uuid4(), db)

    assert sub.status == "trialing"
    assert status == "trialing"
    db.commit.assert_not_awaited()


async def test_check_and_expire_trial_returns_none_when_no_sub():
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = None
    db.execute = AsyncMock(return_value=result)

    status = await check_and_expire_trial(uuid.uuid4(), db)

    assert status is None
    db.commit.assert_not_awaited()


# ---------------------------------------------------------------------------
# check_trial_not_expired
# ---------------------------------------------------------------------------

def _db_with_status(status: str):
    sub = MagicMock()
    sub.status = status
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = sub
    db.execute = AsyncMock(return_value=result)
    return db


async def test_check_trial_not_expired_raises_403():
    db = _db_with_status("trial_expired")

    with pytest.raises(HTTPException) as exc_info:
        await check_trial_not_expired(uuid.uuid4(), db, "create campaigns")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["error"]["code"] == "TRIAL_EXPIRED"
    assert "create campaigns" in exc_info.value.detail["error"]["message"]


async def test_check_trial_not_expired_passes_for_active():
    db = _db_with_status("active")
    # Should not raise
    await check_trial_not_expired(uuid.uuid4(), db)


# ---------------------------------------------------------------------------
# _handle_subscription_updated clears deletion_scheduled_at on active status
# ---------------------------------------------------------------------------

async def test_handle_subscription_updated_clears_deletion_scheduled_at():
    sub = _make_sub(status="trial_expired")
    sub.deletion_scheduled_at = datetime(2026, 7, 20, tzinfo=timezone.utc)
    db = _db_with_sub(sub)

    event = _make_event("customer.subscription.updated", status="active")
    await handle_stripe_webhook(event, db)

    assert sub.status == "active"
    assert sub.deletion_scheduled_at is None
    db.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# PLAN_LIMITS constants (Story 8-9: pricing tier revision)
# ---------------------------------------------------------------------------

def test_plan_limits_starter_clients_is_2():
    assert PLAN_LIMITS["starter"]["clients"] == 2


def test_plan_limits_agency_clients_is_20():
    assert PLAN_LIMITS["agency"]["clients"] == 20


def test_plan_limits_agency_unlimited_sentinel():
    assert PLAN_LIMITS["agency"]["campaigns"] >= UNLIMITED


# ---------------------------------------------------------------------------
# check_campaign_limit — Agency bypass (Story 8-9)
# ---------------------------------------------------------------------------

def _make_agency_sub(campaigns_used: int):
    sub = MagicMock()
    sub.status = "active"
    sub.plan_tier = "agency"
    sub.campaigns_used = campaigns_used
    return sub


def _db_with_for_update_sub(sub):
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = sub
    db.execute = AsyncMock(return_value=result)
    return db


async def test_check_campaign_limit_agency_bypasses_limit():
    """Agency plan must never raise even when campaigns_used is at the sentinel."""
    sub = _make_agency_sub(campaigns_used=999_999)
    db = _db_with_for_update_sub(sub)

    # Must not raise HTTPException
    await check_campaign_limit(db, uuid.uuid4())

    assert sub.campaigns_used == 1_000_000
    db.flush.assert_awaited_once()


# ---------------------------------------------------------------------------
# create_checkout_session (Story 7-4)
# ---------------------------------------------------------------------------

PRICE_MAP = {
    "price_starter_test": "starter",
    "price_growth_test": "growth",
    "price_agency_test": "agency",
}


def _make_user(stripe_customer_id=None, email="user@example.com"):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = email
    user.stripe_customer_id = stripe_customer_id
    return user


def _db_with_user(user):
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = user
    db.execute = AsyncMock(return_value=result)
    return db


async def test_create_checkout_session_valid_plan():
    user = _make_user(stripe_customer_id="cus_existing")
    db = _db_with_user(user)

    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/test_abc123"

    with patch("app.services.subscription_service.get_stripe_price_to_tier", return_value=PRICE_MAP), \
         patch("app.services.subscription_service.stripe_sdk.checkout.Session.create", return_value=mock_session) as mock_create, \
         patch("app.services.subscription_service.settings") as mock_settings:
        mock_settings.APP_URL = "https://personnapress.com"

        result = await create_checkout_session(str(user.id), "growth", db)

    assert result == "https://checkout.stripe.com/test_abc123"
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["mode"] == "subscription"
    assert call_kwargs["line_items"][0]["price"] == "price_growth_test"
    assert call_kwargs["success_url"] == "https://personnapress.com/account?checkout_success=1"
    assert call_kwargs["cancel_url"] == "https://personnapress.com/pricing"
    assert call_kwargs["allow_promotion_codes"] is True
    assert call_kwargs["client_reference_id"] == str(user.id)


async def test_create_checkout_session_uses_existing_customer():
    user = _make_user(stripe_customer_id="cus_123")
    db = _db_with_user(user)

    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/test_existing"

    with patch("app.services.subscription_service.get_stripe_price_to_tier", return_value=PRICE_MAP), \
         patch("app.services.subscription_service.stripe_sdk.checkout.Session.create", return_value=mock_session) as mock_create, \
         patch("app.services.subscription_service.settings") as mock_settings:
        mock_settings.APP_URL = "https://personnapress.com"

        await create_checkout_session(str(user.id), "growth", db)

    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs.get("customer") == "cus_123"
    assert "customer_email" not in call_kwargs
    assert call_kwargs["client_reference_id"] == str(user.id)


async def test_create_checkout_session_new_customer_uses_email():
    user = _make_user(stripe_customer_id=None, email="newuser@example.com")
    db = _db_with_user(user)

    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/test_new"

    with patch("app.services.subscription_service.get_stripe_price_to_tier", return_value=PRICE_MAP), \
         patch("app.services.subscription_service.stripe_sdk.checkout.Session.create", return_value=mock_session) as mock_create, \
         patch("app.services.subscription_service.settings") as mock_settings:
        mock_settings.APP_URL = "https://personnapress.com"

        await create_checkout_session(str(user.id), "starter", db)

    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs.get("customer_email") == "newuser@example.com"
    assert "customer" not in call_kwargs
    assert call_kwargs["client_reference_id"] == str(user.id)


async def test_create_checkout_session_invalid_plan():
    user = _make_user()
    db = _db_with_user(user)

    with patch("app.services.subscription_service.get_stripe_price_to_tier", return_value=PRICE_MAP), \
         patch("app.services.subscription_service.settings") as mock_settings:
        mock_settings.APP_URL = "https://personnapress.com"

        with pytest.raises(HTTPException) as exc_info:
            await create_checkout_session(str(user.id), "enterprise", db)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "INVALID_PLAN"
    db.execute.assert_not_called()


async def test_create_checkout_session_blocks_active_subscriber():
    user = _make_user(stripe_customer_id="cus_active")
    active_sub = MagicMock()
    active_sub.status = "active"

    user_result = MagicMock()
    user_result.scalars.return_value.first.return_value = user
    sub_result = MagicMock()
    sub_result.scalars.return_value.first.return_value = active_sub

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[user_result, sub_result])

    with patch("app.services.subscription_service.get_stripe_price_to_tier", return_value=PRICE_MAP), \
         patch("app.services.subscription_service.settings") as mock_settings:
        mock_settings.APP_URL = "https://personnapress.com"

        with pytest.raises(HTTPException) as exc_info:
            await create_checkout_session(str(user.id), "growth", db)

    assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# check_roadmap_limit (Story 20-1)
# ---------------------------------------------------------------------------

def _make_roadmap_sub(plan_tier: str, roadmaps_used: int, status: str = "active"):
    sub = MagicMock()
    sub.status = status
    sub.plan_tier = plan_tier
    sub.roadmaps_used = roadmaps_used
    return sub


def _db_with_roadmap_sub(sub):
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = sub
    db.execute = AsyncMock(return_value=result)
    return db


async def test_check_roadmap_limit_starter_allows_first():
    """Starter user at roadmaps_used=0 should pass and increment to 1."""
    sub = _make_roadmap_sub("starter", roadmaps_used=0)
    db = _db_with_roadmap_sub(sub)

    await check_roadmap_limit(db, uuid.uuid4())

    assert sub.roadmaps_used == 1
    db.flush.assert_awaited_once()


async def test_check_roadmap_limit_starter_blocks_at_1():
    """Starter user at roadmaps_used=1 (limit=1) should raise 400."""
    sub = _make_roadmap_sub("starter", roadmaps_used=1)
    db = _db_with_roadmap_sub(sub)

    with pytest.raises(HTTPException) as exc_info:
        await check_roadmap_limit(db, uuid.uuid4())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "ROADMAP_LIMIT_EXCEEDED"
    assert "Growth" in exc_info.value.detail["error"]["message"]


async def test_check_roadmap_limit_agency_bypasses():
    """Agency plan should never raise and should still increment counter."""
    sub = _make_roadmap_sub("agency", roadmaps_used=999_999)
    db = _db_with_roadmap_sub(sub)

    await check_roadmap_limit(db, uuid.uuid4())

    assert sub.roadmaps_used == 1_000_000
    db.flush.assert_awaited_once()


# ---------------------------------------------------------------------------
# check_image_limit_batch (Story 20-1)
# ---------------------------------------------------------------------------

def _make_image_sub(plan_tier: str, image_gen_used: int, status: str = "active"):
    sub = MagicMock()
    sub.status = status
    sub.plan_tier = plan_tier
    sub.image_gen_used = image_gen_used
    return sub


def _db_with_image_sub(sub):
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = sub
    db.execute = AsyncMock(return_value=result)
    return db


async def test_check_image_limit_batch_partial_allocation():
    """Starter with 3 remaining out of 10; request 5 → allowed=3, blocked=2."""
    sub = _make_image_sub("starter", image_gen_used=7)  # 7 used, 10 limit → 3 remaining
    db = _db_with_image_sub(sub)

    allowed, blocked = await check_image_limit_batch(db, uuid.uuid4(), 5)

    assert allowed == 3
    assert blocked == 2


async def test_check_image_limit_batch_zero_remaining():
    """User at limit gets allowed=0, blocked=N without raising."""
    sub = _make_image_sub("starter", image_gen_used=10)  # at limit
    db = _db_with_image_sub(sub)

    allowed, blocked = await check_image_limit_batch(db, uuid.uuid4(), 5)

    assert allowed == 0
    assert blocked == 5
