"""Unit tests for handle_stripe_webhook() in subscription_service.py."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.subscription_service import handle_stripe_webhook


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
