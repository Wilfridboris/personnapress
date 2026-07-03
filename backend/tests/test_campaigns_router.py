"""Unit tests for routers/campaigns.py."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest
from fastapi import HTTPException

from app.schemas.campaign import CampaignCreate, CampaignPatch


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_client(user_id=None, client_id=None):
    c = MagicMock()
    c.id = client_id or uuid.uuid4()
    c.user_id = user_id or uuid.uuid4()
    return c


def _make_campaign(campaign_id=None, client_id=None):
    c = MagicMock()
    c.id = campaign_id or uuid.uuid4()
    c.client_id = client_id or uuid.uuid4()
    c.brain_dump = "This is a sample brain dump with enough content for the test."
    c.blog_html = None
    c.x_post = None
    c.linkedin_post = None
    c.image_url = None
    c.status = "pending_approval"
    c.voice_score = None
    c.rejection_reason = None
    c.scheduled_at = None
    c.image_regen_count = 0
    c.created_at = datetime(2026, 7, 2, 10, 0, 0, tzinfo=timezone.utc)
    c.updated_at = datetime(2026, 7, 2, 10, 0, 0, tzinfo=timezone.utc)
    return c


def _make_job(job_id=None, campaign_id=None):
    j = MagicMock()
    j.id = job_id or uuid.uuid4()
    j.campaign_id = campaign_id
    j.job_type = "generation"
    j.status = "pending"
    return j


def _db_sequence(*values):
    db = AsyncMock()
    results = []
    for v in values:
        r = MagicMock()
        r.scalar_one_or_none.return_value = v
        results.append(r)
    db.execute = AsyncMock(side_effect=results)
    return db


# ── POST /campaigns: happy path ───────────────────────────────────────────────

async def test_create_campaign_returns_202_with_campaign_and_job_ids():
    from app.routers.campaigns import create_new_campaign

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id)
    job = _make_job(campaign_id=campaign.id)

    db = AsyncMock()
    body = CampaignCreate(client_id=client.id, brain_dump="A" * 25)
    background_tasks = MagicMock()

    with (
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
        patch("app.routers.campaigns.check_campaign_limit", AsyncMock(return_value=None)),
        patch("app.routers.campaigns.create_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.campaigns.create_job", AsyncMock(return_value=job)),
    ):
        result = await create_new_campaign(
            body=body,
            background_tasks=background_tasks,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result.campaign_id == campaign.id
    assert result.job_id == job.id
    db.commit.assert_awaited_once()
    background_tasks.add_task.assert_called_once()


# ── POST /campaigns: client not found / not owned → 404 ──────────────────────

async def test_create_campaign_raises_404_when_client_not_found():
    from app.routers.campaigns import create_new_campaign

    db = AsyncMock()
    body = CampaignCreate(client_id=uuid.uuid4(), brain_dump="A" * 25)

    with (
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=None)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await create_new_campaign(
                body=body,
                background_tasks=MagicMock(),
                current_user={"user_id": str(uuid.uuid4())},
                db=db,
            )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["error"]["code"] == "CLIENT_NOT_FOUND"


async def test_create_campaign_raises_404_when_client_belongs_to_other_user():
    from app.routers.campaigns import create_new_campaign

    owner_id = uuid.uuid4()
    requester_id = uuid.uuid4()
    client = _make_client(user_id=owner_id)

    db = AsyncMock()
    body = CampaignCreate(client_id=client.id, brain_dump="A" * 25)

    with (
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await create_new_campaign(
                body=body,
                background_tasks=MagicMock(),
                current_user={"user_id": str(requester_id)},
                db=db,
            )

    assert exc_info.value.status_code == 404


# ── POST /campaigns: campaign limit exceeded → 400 ────────────────────────────

async def test_create_campaign_raises_400_when_limit_exceeded():
    from app.routers.campaigns import create_new_campaign

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)

    db = AsyncMock()
    body = CampaignCreate(client_id=client.id, brain_dump="A" * 25)

    limit_error = HTTPException(
        status_code=400,
        detail={"error": {"code": "CAMPAIGN_LIMIT_EXCEEDED", "message": "limit reached", "detail": {}}},
    )

    with (
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
        patch("app.routers.campaigns.check_campaign_limit", AsyncMock(side_effect=limit_error)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await create_new_campaign(
                body=body,
                background_tasks=MagicMock(),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "CAMPAIGN_LIMIT_EXCEEDED"


# ── POST /campaigns: Pydantic rejects brain_dump < 20 chars → 422 ─────────────

async def test_create_campaign_schema_rejects_brain_dump_too_short():
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        CampaignCreate(client_id=uuid.uuid4(), brain_dump="short")


async def test_create_campaign_schema_rejects_brain_dump_over_10000_chars():
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        CampaignCreate(client_id=uuid.uuid4(), brain_dump="A" * 10001)


# ── GET /campaigns/{id}: happy path ──────────────────────────────────────────

async def test_get_campaign_returns_200_for_owner():
    from app.routers.campaigns import get_campaign_by_id

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id)

    db = AsyncMock()

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
    ):
        result = await get_campaign_by_id(
            campaign_id=campaign.id,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result.id == campaign.id
    assert result.status == "pending_approval"


# ── GET /campaigns/{id}: wrong user → 404 ────────────────────────────────────

async def test_get_campaign_raises_404_for_non_owner():
    from app.routers.campaigns import get_campaign_by_id

    owner_id = uuid.uuid4()
    requester_id = uuid.uuid4()
    client = _make_client(user_id=owner_id)
    campaign = _make_campaign(client_id=client.id)

    db = AsyncMock()

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_campaign_by_id(
                campaign_id=campaign.id,
                current_user={"user_id": str(requester_id)},
                db=db,
            )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["error"]["code"] == "CAMPAIGN_NOT_FOUND"


# ── GET /campaigns/{id}: not found → 404 ─────────────────────────────────────

async def test_get_campaign_raises_404_when_not_found():
    from app.routers.campaigns import get_campaign_by_id

    db = AsyncMock()

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=None)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_campaign_by_id(
                campaign_id=uuid.uuid4(),
                current_user={"user_id": str(uuid.uuid4())},
                db=db,
            )

    assert exc_info.value.status_code == 404


# ── POST /campaigns/{id}/image/regenerate ─────────────────────────────────────

async def test_regenerate_image_returns_200_on_success():
    from app.routers.campaigns import regenerate_campaign_image

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id)

    db = AsyncMock()

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
        patch(
            "app.routers.campaigns.image_service.regenerate_image",
            AsyncMock(return_value=("https://supabase.co/new.png", 1)),
        ),
    ):
        result = await regenerate_campaign_image(
            campaign_id=campaign.id,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result.image_url == "https://supabase.co/new.png"
    assert result.image_regen_count == 1


async def test_regenerate_image_raises_400_at_limit():
    from app.routers.campaigns import regenerate_campaign_image

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id)

    db = AsyncMock()

    limit_error = HTTPException(
        status_code=400,
        detail={"error": {"code": "IMAGE_REGEN_LIMIT_REACHED", "message": "0 regenerations remaining.", "detail": {}}},
    )

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
        patch(
            "app.routers.campaigns.image_service.regenerate_image",
            AsyncMock(side_effect=limit_error),
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await regenerate_campaign_image(
                campaign_id=campaign.id,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "IMAGE_REGEN_LIMIT_REACHED"


async def test_regenerate_image_raises_404_for_wrong_user():
    from app.routers.campaigns import regenerate_campaign_image

    owner_id = uuid.uuid4()
    requester_id = uuid.uuid4()
    client = _make_client(user_id=owner_id)
    campaign = _make_campaign(client_id=client.id)

    db = AsyncMock()

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await regenerate_campaign_image(
                campaign_id=campaign.id,
                current_user={"user_id": str(requester_id)},
                db=db,
            )

    assert exc_info.value.status_code == 404


# ── PATCH /campaigns/{id}: happy path ────────────────────────────────────────

async def test_patch_campaign_returns_200_for_owner():
    from app.routers.campaigns import patch_campaign

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id)
    campaign.status = "pending_approval"

    db = AsyncMock()
    body = CampaignPatch(blog_html="<p>Updated</p>")

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
        patch("app.routers.campaigns.nh3.clean", return_value="<p>Updated</p>"),
    ):
        result = await patch_campaign(
            campaign_id=campaign.id,
            body=body,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result.id == campaign.id
    db.commit.assert_awaited_once()


# ── PATCH /campaigns/{id}: wrong status → 400 ────────────────────────────────

async def test_patch_campaign_raises_400_when_not_pending_approval():
    from app.routers.campaigns import patch_campaign

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id)
    campaign.status = "published"

    db = AsyncMock()
    body = CampaignPatch(blog_html="<p>Updated</p>")

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await patch_campaign(
                campaign_id=campaign.id,
                body=body,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "INVALID_STATUS_FOR_EDIT"


# ── PATCH /campaigns/{id}: wrong user → 404 ──────────────────────────────────

async def test_patch_campaign_raises_404_for_non_owner():
    from app.routers.campaigns import patch_campaign

    owner_id = uuid.uuid4()
    requester_id = uuid.uuid4()
    client = _make_client(user_id=owner_id)
    campaign = _make_campaign(client_id=client.id)
    campaign.status = "pending_approval"

    db = AsyncMock()
    body = CampaignPatch(blog_html="<p>Updated</p>")

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await patch_campaign(
                campaign_id=campaign.id,
                body=body,
                current_user={"user_id": str(requester_id)},
                db=db,
            )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["error"]["code"] == "CAMPAIGN_NOT_FOUND"


# ── POST /campaigns: 401 on invalid session ───────────────────────────────────

async def test_create_campaign_raises_401_on_bad_session():
    from app.routers.campaigns import create_new_campaign

    with pytest.raises(HTTPException) as exc_info:
        await create_new_campaign(
            body=CampaignCreate(client_id=uuid.uuid4(), brain_dump="A" * 25),
            background_tasks=MagicMock(),
            current_user={},
            db=AsyncMock(),
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["error"]["code"] == "INVALID_SESSION"
