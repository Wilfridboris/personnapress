"""Unit tests for PATCH /clients/{id} and DELETE /clients/{id}."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.schemas.client import ClientUpdate


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_client(user_id: uuid.UUID | None = None, name: str = "Acme", url: str | None = None):
    c = MagicMock()
    c.id = uuid.uuid4()
    c.user_id = user_id or uuid.uuid4()
    c.name = name
    c.website_url = url
    c.brand_voice_profile = None
    c.created_at = "2026-01-01T00:00:00Z"
    return c


def _db_scalar(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _db_scalar_one(value):
    r = MagicMock()
    r.scalar_one.return_value = value
    return r


# ── ClientUpdate schema ───────────────────────────────────────────────────────

async def test_client_update_schema_allows_all_none():
    obj = ClientUpdate()
    assert obj.name is None
    assert obj.website_url is None
    assert obj.confirm_url_change is False


async def test_client_update_schema_rejects_empty_name():
    import pydantic
    with pytest.raises(pydantic.ValidationError):
        ClientUpdate(name="   ")


async def test_client_update_schema_rejects_bad_url():
    import pydantic
    with pytest.raises(pydantic.ValidationError):
        ClientUpdate(website_url="not-a-url")


async def test_client_update_schema_accepts_valid_url():
    obj = ClientUpdate(name="Acme", website_url="https://example.com")
    assert obj.website_url == "https://example.com"
    assert obj.name == "Acme"


async def test_client_update_schema_empty_url_becomes_none():
    obj = ClientUpdate(website_url="  ")
    assert obj.website_url is None


# ── Repository: get_campaign_count ────────────────────────────────────────────

async def test_get_campaign_count_returns_integer():
    from app.db.repositories.clients import get_campaign_count

    db = AsyncMock()
    db.execute.return_value = _db_scalar_one(5)
    count = await get_campaign_count(db, uuid.uuid4())
    assert count == 5


async def test_get_campaign_count_returns_zero_when_none():
    from app.db.repositories.clients import get_campaign_count

    db = AsyncMock()
    db.execute.return_value = _db_scalar_one(0)
    count = await get_campaign_count(db, uuid.uuid4())
    assert count == 0


# ── Router: PATCH /clients/{client_id} ───────────────────────────────────────

@patch("app.routers.clients.get_client")
@patch("app.routers.clients.get_current_user")
async def test_patch_client_invalid_session_returns_401(mock_get_user, mock_get_client):
    from app.routers.clients import update_client_detail

    mock_get_user.return_value = {}  # missing user_id key
    db = AsyncMock()
    bg = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await update_client_detail(uuid.uuid4(), ClientUpdate(name="X"), bg, {}, db)

    assert exc_info.value.status_code == 401


@patch("app.routers.clients.get_client")
async def test_patch_client_not_found_returns_404(mock_get_client):
    from app.routers.clients import update_client_detail

    mock_get_client.return_value = None
    user_id = uuid.uuid4()
    current_user = {"user_id": str(user_id)}
    db = AsyncMock()
    bg = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await update_client_detail(uuid.uuid4(), ClientUpdate(name="X"), bg, current_user, db)

    assert exc_info.value.status_code == 404


@patch("app.routers.clients.get_client")
async def test_patch_client_wrong_owner_returns_403(mock_get_client):
    from app.routers.clients import update_client_detail

    owner_id = uuid.uuid4()
    requester_id = uuid.uuid4()
    client = _make_client(user_id=owner_id)
    mock_get_client.return_value = client
    current_user = {"user_id": str(requester_id)}
    db = AsyncMock()
    bg = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await update_client_detail(client.id, ClientUpdate(name="X"), bg, current_user, db)

    assert exc_info.value.status_code == 403


@patch("app.routers.clients.get_campaign_count")
@patch("app.routers.clients.get_active_ingestion_job_for_client")
@patch("app.routers.clients.update_client")
@patch("app.routers.clients.get_client")
async def test_patch_client_name_only_does_not_trigger_reanalysis(
    mock_get_client, mock_update, mock_active_job, mock_campaign_count
):
    from app.routers.clients import update_client_detail

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id, name="Old Name", url="https://same.com")
    updated = _make_client(user_id=user_id, name="New Name", url="https://same.com")
    updated.id = client.id
    mock_get_client.return_value = client
    mock_update.return_value = updated
    mock_active_job.return_value = None
    mock_campaign_count.return_value = 0
    current_user = {"user_id": str(user_id)}
    db = AsyncMock()
    bg = MagicMock()

    result = await update_client_detail(
        client.id, ClientUpdate(name="New Name"), bg, current_user, db
    )

    assert result.name == "New Name"
    db.commit.assert_called_once()
    bg.add_task.assert_not_called()


@patch("app.routers.clients.get_client")
async def test_patch_client_url_change_without_confirm_returns_requires_confirmation(
    mock_get_client,
):
    from app.routers.clients import update_client_detail

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id, url="https://old.com")
    mock_get_client.return_value = client
    current_user = {"user_id": str(user_id)}
    db = AsyncMock()
    bg = MagicMock()

    result = await update_client_detail(
        client.id,
        ClientUpdate(website_url="https://new.com", confirm_url_change=False),
        bg,
        current_user,
        db,
    )

    assert result == {"requires_confirmation": True, "domain": "new.com"}
    db.commit.assert_not_called()
    bg.add_task.assert_not_called()


@patch("app.routers.clients.get_campaign_count")
@patch("app.routers.clients.ingest_worker")
@patch("app.routers.clients.create_job")
@patch("app.routers.clients.update_client")
@patch("app.routers.clients.get_client")
async def test_patch_client_url_change_with_confirm_dispatches_ingest(
    mock_get_client, mock_update, mock_create_job, mock_ingest, mock_campaign_count
):
    from app.routers.clients import update_client_detail

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id, url="https://old.com")
    updated = _make_client(user_id=user_id, url="https://new.com")
    updated.id = client.id
    job = MagicMock()
    job.id = uuid.uuid4()
    mock_get_client.return_value = client
    mock_update.return_value = updated
    mock_create_job.return_value = job
    mock_campaign_count.return_value = 0
    current_user = {"user_id": str(user_id)}
    db = AsyncMock()
    bg = MagicMock()

    result = await update_client_detail(
        client.id,
        ClientUpdate(website_url="https://new.com", confirm_url_change=True),
        bg,
        current_user,
        db,
    )

    assert result.job_id == job.id
    bg.add_task.assert_called_once()
    db.commit.assert_called_once()


# ── Router: DELETE /clients/{client_id} ──────────────────────────────────────

@patch("app.routers.clients.get_client")
async def test_delete_client_not_found_returns_404(mock_get_client):
    from app.routers.clients import delete_client_detail

    mock_get_client.return_value = None
    user_id = uuid.uuid4()
    current_user = {"user_id": str(user_id)}
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await delete_client_detail(uuid.uuid4(), current_user, db)

    assert exc_info.value.status_code == 404


@patch("app.routers.clients.get_client")
async def test_delete_client_wrong_owner_returns_403(mock_get_client):
    from app.routers.clients import delete_client_detail

    owner_id = uuid.uuid4()
    requester_id = uuid.uuid4()
    client = _make_client(user_id=owner_id)
    mock_get_client.return_value = client
    current_user = {"user_id": str(requester_id)}
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await delete_client_detail(client.id, current_user, db)

    assert exc_info.value.status_code == 403


@patch("app.routers.clients.delete_client")
@patch("app.routers.clients.get_client")
async def test_delete_client_success_returns_204(mock_get_client, mock_delete):
    from app.routers.clients import delete_client_detail

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    mock_get_client.return_value = client
    mock_delete.return_value = None
    current_user = {"user_id": str(user_id)}
    db = AsyncMock()

    response = await delete_client_detail(client.id, current_user, db)

    assert response.status_code == 204
    mock_delete.assert_called_once_with(db, client.id)
    db.commit.assert_called_once()


@patch("app.routers.clients.get_client")
async def test_delete_client_invalid_session_returns_401(mock_get_client):
    from app.routers.clients import delete_client_detail

    db = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await delete_client_detail(uuid.uuid4(), {}, db)

    assert exc_info.value.status_code == 401
