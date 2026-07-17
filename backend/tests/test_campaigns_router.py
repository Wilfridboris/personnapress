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
    c.github_pr_url = None
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


# ── POST /campaigns: secondary_keywords field (Story 3-10) ───────────────────

def test_campaign_create_schema_validates_secondary_keywords():
    body = CampaignCreate(
        client_id=uuid.uuid4(),
        brain_dump="A" * 25,
        secondary_keywords="term1, term2",
    )
    assert body.secondary_keywords == "term1, term2"


def test_campaign_create_nullifies_blank_secondary_keywords():
    body = CampaignCreate(
        client_id=uuid.uuid4(),
        brain_dump="A" * 25,
        secondary_keywords="   ",
    )
    assert body.secondary_keywords is None


def test_campaign_create_secondary_keywords_defaults_to_none():
    body = CampaignCreate(client_id=uuid.uuid4(), brain_dump="A" * 25)
    assert body.secondary_keywords is None


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


# ── POST /campaigns/{id}/approve ─────────────────────────────────────────────

async def test_approve_campaign_transitions_status_to_approved():
    from app.routers.campaigns import approve_campaign

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id)
    campaign.status = "pending_approval"
    db = AsyncMock()

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
    ):
        result = await approve_campaign(
            campaign_id=campaign.id,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert campaign.status == "approved"
    db.add.assert_called_once_with(campaign)
    db.commit.assert_awaited_once()
    assert result.status == "approved"
    assert result.client_id == campaign.client_id


async def test_approve_campaign_returns_400_for_wrong_status():
    from app.routers.campaigns import approve_campaign

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id)
    campaign.status = "rejected"
    db = AsyncMock()

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await approve_campaign(
                campaign_id=campaign.id,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "INVALID_STATUS_TRANSITION"


async def test_approve_campaign_returns_404_when_not_owned():
    from app.routers.campaigns import approve_campaign

    user_id = uuid.uuid4()
    other_client = _make_client(user_id=uuid.uuid4())
    campaign = _make_campaign(client_id=other_client.id)
    db = AsyncMock()

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=other_client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await approve_campaign(
                campaign_id=campaign.id,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 404


# ── POST /campaigns/{id}/reject ──────────────────────────────────────────────

async def test_reject_campaign_with_reason_saves_reason():
    from app.routers.campaigns import reject_campaign, RejectRequest

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id)
    campaign.status = "pending_approval"
    db = AsyncMock()

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
    ):
        result = await reject_campaign(
            campaign_id=campaign.id,
            body=RejectRequest(reason="Too generic"),
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert campaign.status == "rejected"
    assert campaign.rejection_reason == "Too generic"
    assert result.status == "rejected"


async def test_reject_campaign_without_reason():
    from app.routers.campaigns import reject_campaign, RejectRequest

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id)
    campaign.status = "pending_approval"
    db = AsyncMock()

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
    ):
        result = await reject_campaign(
            campaign_id=campaign.id,
            body=RejectRequest(reason=None),
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert campaign.status == "rejected"
    assert result.status == "rejected"


async def test_reject_campaign_wrong_status_returns_400():
    from app.routers.campaigns import reject_campaign, RejectRequest

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id)
    campaign.status = "approved"
    db = AsyncMock()

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await reject_campaign(
                campaign_id=campaign.id,
                body=RejectRequest(reason=None),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "INVALID_STATUS_TRANSITION"


# ── POST /campaigns/{id}/regenerate ──────────────────────────────────────────

async def test_regenerate_campaign_creates_new_campaign_and_job():
    from app.routers.campaigns import regenerate_campaign

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    source = _make_campaign(client_id=client.id)
    source.status = "rejected"
    new_campaign = _make_campaign(client_id=client.id)
    new_job = _make_job(campaign_id=new_campaign.id)
    db = AsyncMock()
    background_tasks = MagicMock()

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=source)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
        patch("app.routers.campaigns.check_campaign_limit", AsyncMock(return_value=None)),
        patch("app.routers.campaigns.create_campaign", AsyncMock(return_value=new_campaign)),
        patch("app.routers.campaigns.create_job", AsyncMock(return_value=new_job)),
    ):
        result = await regenerate_campaign(
            campaign_id=source.id,
            background_tasks=background_tasks,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    # Source campaign status unchanged
    assert source.status == "rejected"
    assert result.campaign_id == new_campaign.id
    assert result.job_id == new_job.id
    db.commit.assert_awaited_once()
    background_tasks.add_task.assert_called_once()


async def test_regenerate_campaign_only_from_rejected_status():
    from app.routers.campaigns import regenerate_campaign

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id)
    campaign.status = "pending_approval"
    db = AsyncMock()

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await regenerate_campaign(
                campaign_id=campaign.id,
                background_tasks=MagicMock(),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "INVALID_STATUS_TRANSITION"


# ── POST /campaigns/{id}/revoice ─────────────────────────────────────────────


async def test_revoice_campaign_approved_returns_202_with_ids():
    from app.routers.campaigns import revoice_campaign

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    source = _make_campaign(client_id=client.id)
    source.status = "approved"
    source.brain_dump = "Original brain dump content for revoice."
    new_campaign = _make_campaign(client_id=client.id)
    new_job = _make_job(campaign_id=new_campaign.id)
    db = AsyncMock()
    background_tasks = MagicMock()

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=source)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
        patch("app.routers.campaigns.create_campaign", AsyncMock(return_value=new_campaign)),
        patch("app.routers.campaigns.create_job", AsyncMock(return_value=new_job)),
    ):
        result = await revoice_campaign(
            campaign_id=source.id,
            background_tasks=background_tasks,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result.new_campaign_id == new_campaign.id
    assert result.job_id == new_job.id
    db.commit.assert_awaited_once()
    background_tasks.add_task.assert_called_once()


async def test_revoice_campaign_published_returns_202():
    from app.routers.campaigns import revoice_campaign

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    source = _make_campaign(client_id=client.id)
    source.status = "published"
    source.brain_dump = "Original brain dump content."
    new_campaign = _make_campaign(client_id=client.id)
    new_job = _make_job(campaign_id=new_campaign.id)
    db = AsyncMock()

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=source)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
        patch("app.routers.campaigns.create_campaign", AsyncMock(return_value=new_campaign)),
        patch("app.routers.campaigns.create_job", AsyncMock(return_value=new_job)),
    ):
        result = await revoice_campaign(
            campaign_id=source.id,
            background_tasks=MagicMock(),
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result.new_campaign_id == new_campaign.id
    assert result.job_id == new_job.id


async def test_revoice_campaign_original_unchanged():
    from app.routers.campaigns import revoice_campaign

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    source = _make_campaign(client_id=client.id)
    source.status = "approved"
    source.brain_dump = "Do not touch this."
    original_status = source.status
    original_brain_dump = source.brain_dump
    new_campaign = _make_campaign(client_id=client.id)
    new_job = _make_job(campaign_id=new_campaign.id)
    db = AsyncMock()
    mock_create_campaign = AsyncMock(return_value=new_campaign)

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=source)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
        patch("app.routers.campaigns.create_campaign", mock_create_campaign),
        patch("app.routers.campaigns.create_job", AsyncMock(return_value=new_job)),
    ):
        await revoice_campaign(
            campaign_id=source.id,
            background_tasks=MagicMock(),
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert source.status == original_status
    assert source.brain_dump == original_brain_dump
    mock_create_campaign.assert_awaited_once_with(db, source.client_id, original_brain_dump)


async def test_revoice_campaign_invalid_status_returns_422():
    from app.routers.campaigns import revoice_campaign

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id)
    campaign.status = "pending_approval"
    db = AsyncMock()

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await revoice_campaign(
                campaign_id=campaign.id,
                background_tasks=MagicMock(),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["error"]["code"] == "REVOICE_INVALID_STATUS"


async def test_revoice_campaign_rejected_status_returns_422():
    from app.routers.campaigns import revoice_campaign

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id)
    campaign.status = "rejected"
    db = AsyncMock()

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await revoice_campaign(
                campaign_id=campaign.id,
                background_tasks=MagicMock(),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["error"]["code"] == "REVOICE_INVALID_STATUS"


async def test_revoice_campaign_null_brain_dump_returns_422():
    from app.routers.campaigns import revoice_campaign

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id)
    campaign.status = "approved"
    campaign.brain_dump = None
    db = AsyncMock()

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await revoice_campaign(
                campaign_id=campaign.id,
                background_tasks=MagicMock(),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["error"]["code"] == "REVOICE_NO_BRAIN_DUMP"


async def test_revoice_campaign_empty_brain_dump_returns_422():
    from app.routers.campaigns import revoice_campaign

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id)
    campaign.status = "approved"
    campaign.brain_dump = ""
    db = AsyncMock()

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await revoice_campaign(
                campaign_id=campaign.id,
                background_tasks=MagicMock(),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["error"]["code"] == "REVOICE_NO_BRAIN_DUMP"


async def test_revoice_campaign_whitespace_brain_dump_returns_422():
    from app.routers.campaigns import revoice_campaign

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id)
    campaign.status = "approved"
    campaign.brain_dump = "   \n\t  "
    db = AsyncMock()

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await revoice_campaign(
                campaign_id=campaign.id,
                background_tasks=MagicMock(),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["error"]["code"] == "REVOICE_NO_BRAIN_DUMP"


async def test_revoice_campaign_failed_status_returns_422():
    from app.routers.campaigns import revoice_campaign

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    campaign = _make_campaign(client_id=client.id)
    campaign.status = "failed"
    db = AsyncMock()

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await revoice_campaign(
                campaign_id=campaign.id,
                background_tasks=MagicMock(),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["error"]["code"] == "REVOICE_INVALID_STATUS"


async def test_revoice_campaign_unauthenticated_returns_401():
    from app.routers.campaigns import revoice_campaign

    with pytest.raises(HTTPException) as exc_info:
        await revoice_campaign(
            campaign_id=uuid.uuid4(),
            background_tasks=MagicMock(),
            current_user={},
            db=AsyncMock(),
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["error"]["code"] == "INVALID_SESSION"


async def test_revoice_campaign_wrong_user_returns_403():
    from app.routers.campaigns import revoice_campaign

    owner_id = uuid.uuid4()
    requester_id = uuid.uuid4()
    client = _make_client(user_id=owner_id)
    campaign = _make_campaign(client_id=client.id)
    campaign.status = "approved"
    campaign.brain_dump = "some content"
    db = AsyncMock()

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await revoice_campaign(
                campaign_id=campaign.id,
                background_tasks=MagicMock(),
                current_user={"user_id": str(requester_id)},
                db=db,
            )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["error"]["code"] == "FORBIDDEN"


# ── Campaign blog_html sanitizer — image handling ─────────────────────────────


def test_sanitize_blog_html_keeps_own_bucket_img():
    """_sanitize_blog_html preserves <img> with an own-bucket src."""
    from app.routers.campaigns import _sanitize_blog_html
    from app.core.config import settings

    original_url = settings.SUPABASE_URL
    settings.SUPABASE_URL = "https://test.supabase.co"
    try:
        src = "https://test.supabase.co/storage/v1/object/public/article-images/chart.png"
        result = _sanitize_blog_html(f'<p>text</p><img src="{src}" alt="Chart">')
        assert "img" in result
        assert src in result
    finally:
        settings.SUPABASE_URL = original_url


def test_sanitize_blog_html_strips_foreign_img():
    """_sanitize_blog_html removes <img> with a foreign src URL."""
    from app.routers.campaigns import _sanitize_blog_html
    from app.core.config import settings

    original_url = settings.SUPABASE_URL
    settings.SUPABASE_URL = "https://test.supabase.co"
    try:
        result = _sanitize_blog_html('<p>text</p><img src="https://evil.com/tracker.png" alt="x">')
        assert "evil.com" not in result
        assert "<img" not in result
    finally:
        settings.SUPABASE_URL = original_url


def test_sanitize_blog_html_strips_img_onerror():
    """_sanitize_blog_html strips onerror attribute from img tags."""
    from app.routers.campaigns import _sanitize_blog_html
    from app.core.config import settings

    original_url = settings.SUPABASE_URL
    settings.SUPABASE_URL = "https://test.supabase.co"
    try:
        src = "https://test.supabase.co/storage/v1/object/public/article-images/ok.png"
        result = _sanitize_blog_html(f'<img src="{src}" alt="x" onerror="alert(1)">')
        assert "onerror" not in result
        assert src in result
    finally:
        settings.SUPABASE_URL = original_url


def test_sanitize_blog_html_strips_srcset():
    """_sanitize_blog_html strips srcset from img tags (nh3 does not allow it)."""
    from app.routers.campaigns import _sanitize_blog_html
    from app.core.config import settings

    original_url = settings.SUPABASE_URL
    settings.SUPABASE_URL = "https://test.supabase.co"
    try:
        src = "https://test.supabase.co/storage/v1/object/public/article-images/ok.png"
        result = _sanitize_blog_html(f'<img src="{src}" alt="x" srcset="{src} 2x, {src} 1x">')
        assert "srcset" not in result
        assert src in result  # img itself is preserved; only srcset stripped
    finally:
        settings.SUPABASE_URL = original_url
