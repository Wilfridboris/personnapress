"""Tests for GET /api/v1/campaigns (list_campaigns) endpoint."""
import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

# Stub out heavy transitive imports before any app module is loaded
sys.modules.setdefault("app.workers.generate", MagicMock())
sys.modules.setdefault("app.services.generation", MagicMock())
sys.modules.setdefault("app.integrations.gemini", MagicMock())

import pytest
from fastapi import HTTPException


def _make_campaign(client_id=None, status="pending_approval"):
    c = MagicMock()
    c.id = uuid.uuid4()
    c.client_id = client_id or uuid.uuid4()
    c.status = status
    c.brain_dump = "test brain dump"
    c.blog_html = None
    c.x_post = None
    c.linkedin_post = None
    c.image_url = None
    c.voice_score = None
    c.rejection_reason = None
    c.scheduled_at = None
    c.image_regen_count = 0
    import datetime
    c.created_at = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    c.updated_at = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    return c


def _make_client(user_id=None, client_id=None):
    cl = MagicMock()
    cl.id = client_id or uuid.uuid4()
    cl.user_id = user_id or uuid.uuid4()
    return cl


def _make_db(campaigns, total):
    """Create a mock DB that returns `total` for count and `campaigns` for data query."""
    db = AsyncMock()

    count_result = MagicMock()
    count_result.scalar_one.return_value = total

    data_result = MagicMock()
    data_result.scalars.return_value.all.return_value = campaigns

    # 3rd call: client names lookup (Client.id, Client.name rows)
    names_result = MagicMock()
    names_result.all.return_value = []

    db.execute = AsyncMock(side_effect=[count_result, data_result, names_result])
    return db


async def test_list_campaigns_returns_items_and_total():
    from app.routers.campaigns import list_campaigns

    user_id = uuid.uuid4()
    campaign = _make_campaign()
    db = _make_db([campaign], total=1)

    result = await list_campaigns(
        client_id=None,
        status=None,
        page=1,
        per_page=20,
        current_user={"user_id": str(user_id)},
        db=db,
    )

    assert result.total == 1
    assert len(result.items) == 1


async def test_list_campaigns_with_client_id_filter():
    from app.routers.campaigns import list_campaigns

    user_id = uuid.uuid4()
    client_id = uuid.uuid4()
    client = _make_client(user_id=user_id, client_id=client_id)
    campaign = _make_campaign(client_id=client_id)
    db = _make_db([campaign], total=1)

    with patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)):
        result = await list_campaigns(
            client_id=client_id,
            status=None,
            page=1,
            per_page=20,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result.total == 1
    assert len(result.items) == 1


async def test_list_campaigns_status_filter():
    from app.routers.campaigns import list_campaigns

    user_id = uuid.uuid4()
    campaign = _make_campaign(status="pending_approval")
    db = _make_db([campaign], total=1)

    result = await list_campaigns(
        client_id=None,
        status="pending_approval",
        page=1,
        per_page=20,
        current_user={"user_id": str(user_id)},
        db=db,
    )

    assert result.total == 1
    assert result.items[0].status == "pending_approval"


async def test_list_campaigns_multiple_status():
    from app.routers.campaigns import list_campaigns

    user_id = uuid.uuid4()
    c1 = _make_campaign(status="published")
    c2 = _make_campaign(status="approved")
    db = _make_db([c1, c2], total=2)

    result = await list_campaigns(
        client_id=None,
        status="published,approved",
        page=1,
        per_page=20,
        current_user={"user_id": str(user_id)},
        db=db,
    )

    assert result.total == 2
    assert len(result.items) == 2


async def test_create_campaign_blocked_for_trial_expired():
    from fastapi import HTTPException
    from unittest.mock import patch, AsyncMock
    from app.routers.campaigns import create_new_campaign
    from app.schemas.campaign import CampaignCreate

    user_id = uuid.uuid4()
    client_id = uuid.uuid4()
    client = _make_client(user_id=user_id, client_id=client_id)

    db = AsyncMock()

    trial_expired_error = HTTPException(
        status_code=403,
        detail={
            "error": {
                "code": "TRIAL_EXPIRED",
                "message": "Subscribe to create campaigns.",
                "detail": {"status": "trial_expired"},
            }
        },
    )

    with (
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
        patch(
            "app.routers.campaigns.check_trial_not_expired",
            AsyncMock(side_effect=trial_expired_error),
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await create_new_campaign(
                body=CampaignCreate(client_id=client_id, brain_dump="x" * 25),
                background_tasks=MagicMock(),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["error"]["code"] == "TRIAL_EXPIRED"


async def test_list_campaigns_pagination():
    from app.routers.campaigns import list_campaigns

    user_id = uuid.uuid4()
    campaigns = [_make_campaign() for _ in range(5)]
    db = _make_db(campaigns, total=25)

    result = await list_campaigns(
        client_id=None,
        status=None,
        page=2,
        per_page=5,
        current_user={"user_id": str(user_id)},
        db=db,
    )

    assert result.total == 25
    assert len(result.items) == 5


async def test_list_campaigns_client_id_ownership():
    from app.routers.campaigns import list_campaigns

    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    client_id = uuid.uuid4()
    client = _make_client(user_id=other_user_id, client_id=client_id)
    db = MagicMock()

    with patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)):
        with pytest.raises(HTTPException) as exc_info:
            await list_campaigns(
                client_id=client_id,
                status=None,
                page=1,
                per_page=20,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["error"]["code"] == "FORBIDDEN"


# ── patch_campaign status guard tests ────────────────────────────────────────

def _make_patch_db(campaign):
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


async def test_patch_campaign_approved_succeeds():
    """patch_campaign allows edits when status is approved."""
    from app.routers.campaigns import patch_campaign
    from app.schemas.campaign import CampaignPatch

    user_id = uuid.uuid4()
    campaign = _make_campaign(status="approved")
    client = _make_client(user_id=user_id, client_id=campaign.client_id)
    db = _make_patch_db(campaign)
    body = CampaignPatch(x_post="Updated X post")

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
        patch("app.routers.campaigns.CampaignResponse.model_validate", return_value=MagicMock(status="approved")),
    ):
        result = await patch_campaign(
            campaign_id=campaign.id,
            body=body,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result.status == "approved"
    db.commit.assert_called_once()


async def test_patch_campaign_approved_scheduled_at_unchanged():
    """patch succeeds when approved with future scheduled_at; scheduled_at is not touched."""
    import datetime as dt
    from app.routers.campaigns import patch_campaign
    from app.schemas.campaign import CampaignPatch

    user_id = uuid.uuid4()
    future_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=3)
    campaign = _make_campaign(status="approved")
    campaign.scheduled_at = future_at
    client = _make_client(user_id=user_id, client_id=campaign.client_id)
    db = _make_patch_db(campaign)
    body = CampaignPatch(linkedin_post="Updated LinkedIn")

    original_scheduled_at = campaign.scheduled_at

    with (
        patch("app.routers.campaigns.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.routers.campaigns.get_client", AsyncMock(return_value=client)),
        patch("app.routers.campaigns.CampaignResponse.model_validate", return_value=MagicMock(status="approved")),
    ):
        await patch_campaign(
            campaign_id=campaign.id,
            body=body,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    # scheduled_at must not have been changed by the patch
    assert campaign.scheduled_at == original_scheduled_at


@pytest.mark.parametrize("status", ["published", "rejected", "failed"])
async def test_patch_campaign_terminal_statuses_rejected(status):
    """patch_campaign rejects edits for published, rejected, and failed campaigns."""
    from app.routers.campaigns import patch_campaign
    from app.schemas.campaign import CampaignPatch

    user_id = uuid.uuid4()
    campaign = _make_campaign(status=status)
    client = _make_client(user_id=user_id, client_id=campaign.client_id)
    db = AsyncMock()
    body = CampaignPatch(x_post="Should not apply")

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
