"""Unit tests for check_client_limit() in subscription_service.py."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.services.subscription_service import check_client_limit


def _make_sub(plan_tier: str = "starter"):
    m = MagicMock()
    m.plan_tier = plan_tier
    return m


def _db_scalar(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _db_scalars(rows: list):
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = rows
    r = MagicMock()
    r.scalars.return_value = scalars_mock
    return r


async def test_within_limit_does_not_raise():
    db = AsyncMock()
    db.execute.side_effect = [
        _db_scalar(_make_sub("starter")),
        _db_scalars([MagicMock()]),  # 1 client, limit is 3
    ]
    await check_client_limit(uuid.uuid4(), db)  # must not raise


async def test_at_limit_raises_400():
    db = AsyncMock()
    sub = _make_sub("starter")
    db.execute.side_effect = [
        _db_scalar(sub),
        _db_scalars([MagicMock(), MagicMock(), MagicMock()]),  # 3 clients, limit is 3
    ]
    with pytest.raises(HTTPException) as exc_info:
        await check_client_limit(uuid.uuid4(), db)

    assert exc_info.value.status_code == 400
    err = exc_info.value.detail["error"]
    assert err["code"] == "CLIENT_LIMIT_REACHED"
    assert err["detail"]["limit"] == 3
    assert err["detail"]["plan"] == "starter"
    assert err["detail"]["next_tier"] == "growth"


async def test_growth_limit_reached_suggests_agency():
    db = AsyncMock()
    sub = _make_sub("growth")
    clients = [MagicMock() for _ in range(5)]  # 5 clients, limit is 5
    db.execute.side_effect = [_db_scalar(sub), _db_scalars(clients)]

    with pytest.raises(HTTPException) as exc_info:
        await check_client_limit(uuid.uuid4(), db)

    err = exc_info.value.detail["error"]
    assert err["code"] == "CLIENT_LIMIT_REACHED"
    assert err["detail"]["next_tier"] == "agency"
    assert err["detail"]["next_limit"] == 15


async def test_no_subscription_defaults_to_starter():
    db = AsyncMock()
    db.execute.side_effect = [
        _db_scalar(None),  # no subscription
        _db_scalars([MagicMock() for _ in range(3)]),  # 3 clients → hits starter limit
    ]
    with pytest.raises(HTTPException) as exc_info:
        await check_client_limit(uuid.uuid4(), db)

    assert exc_info.value.detail["error"]["detail"]["limit"] == 3


async def test_client_create_schema_rejects_empty_name():
    from app.schemas.client import ClientCreate
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        ClientCreate(name="   ")


async def test_client_create_schema_rejects_bad_url():
    from app.schemas.client import ClientCreate
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        ClientCreate(name="Acme", website_url="not-a-url")


async def test_client_create_schema_accepts_valid_url():
    from app.schemas.client import ClientCreate

    obj = ClientCreate(name="Acme", website_url="https://example.com")
    assert obj.website_url == "https://example.com"


async def test_client_create_schema_treats_empty_url_as_none():
    from app.schemas.client import ClientCreate

    obj = ClientCreate(name="Acme", website_url="  ")
    assert obj.website_url is None
