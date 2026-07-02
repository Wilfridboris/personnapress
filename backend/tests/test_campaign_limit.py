"""Unit tests for check_campaign_limit() in subscription_service.py."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.services.subscription_service import check_campaign_limit


def _make_sub(plan_tier: str = "starter", campaigns_used: int = 0, status: str = "active"):
    m = MagicMock()
    m.plan_tier = plan_tier
    m.campaigns_used = campaigns_used
    m.status = status
    return m


def _db_with_sub(sub):
    db = AsyncMock()
    r = MagicMock()
    r.scalars.return_value.first.return_value = sub
    db.execute = AsyncMock(return_value=r)
    return db


async def test_within_limit_does_not_raise_and_increments():
    sub = _make_sub("starter", campaigns_used=5)
    db = _db_with_sub(sub)

    await check_campaign_limit(db, uuid.uuid4())  # must not raise
    assert sub.campaigns_used == 6
    db.flush.assert_awaited_once()


async def test_at_limit_raises_400_with_correct_code():
    sub = _make_sub("starter", campaigns_used=10)  # limit is 10
    db = _db_with_sub(sub)

    with pytest.raises(HTTPException) as exc_info:
        await check_campaign_limit(db, uuid.uuid4())

    assert exc_info.value.status_code == 400
    err = exc_info.value.detail["error"]
    assert err["code"] == "CAMPAIGN_LIMIT_EXCEEDED"
    assert err["detail"]["limit"] == 10
    assert err["detail"]["plan"] == "starter"
    assert err["detail"]["next_tier"] == "growth"


async def test_growth_tier_limit_exceeded_suggests_agency():
    sub = _make_sub("growth", campaigns_used=30)  # limit is 30
    db = _db_with_sub(sub)

    with pytest.raises(HTTPException) as exc_info:
        await check_campaign_limit(db, uuid.uuid4())

    err = exc_info.value.detail["error"]
    assert err["detail"]["next_tier"] == "agency"
    assert err["detail"]["limit"] == 30


async def test_no_subscription_defaults_to_starter_zero_used():
    db = AsyncMock()
    sub_result = MagicMock()
    sub_result.scalars.return_value.first.return_value = None
    count_result = MagicMock()
    count_result.scalar.return_value = 0
    db.execute = AsyncMock(side_effect=[sub_result, count_result])  # sub query + campaign count

    # With 0 campaigns and starter limit 10, should not raise
    await check_campaign_limit(db, uuid.uuid4())


async def test_canceled_subscription_uses_starter_limits():
    sub = _make_sub("agency", campaigns_used=10, status="canceled")
    db = _db_with_sub(sub)

    # Canceled sub → treated as starter (limit 10), at 10 → raises
    with pytest.raises(HTTPException) as exc_info:
        await check_campaign_limit(db, uuid.uuid4())

    assert exc_info.value.status_code == 400
    err = exc_info.value.detail["error"]
    assert err["detail"]["limit"] == 10
