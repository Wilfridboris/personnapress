"""Tests for GET /api/v1/analytics/clients/{client_id}/summary and /posts."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _user_id():
    return uuid.uuid4()


def _client_id():
    return uuid.uuid4()


def _make_client(user_id, client_id=None):
    c = MagicMock()
    c.id = client_id or uuid.uuid4()
    c.user_id = user_id
    return c


# ---------------------------------------------------------------------------
# Summary endpoint tests
# ---------------------------------------------------------------------------

async def test_summary_returns_200_for_valid_client():
    from app.routers.analytics import client_analytics_summary

    user_id = _user_id()
    client_id = _client_id()
    client = _make_client(user_id, client_id)

    from app.schemas.analytics import ClientSummaryResponse
    mock_summary = ClientSummaryResponse(
        client_id=client_id,
        total_impressions=1000,
        total_engagements=50,
        posts_tracked=3,
        best_post=None,
        freshest_captured_at=None,
    )

    request = MagicMock()
    db = AsyncMock()

    with (
        patch("app.routers.analytics.get_current_user", return_value={"user_id": str(user_id)}),
        patch("app.routers.analytics.get_client", AsyncMock(return_value=client)),
        patch("app.routers.analytics.get_client_summary", AsyncMock(return_value=mock_summary)),
    ):
        result = await client_analytics_summary(
            request=request,
            client_id=client_id,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result.client_id == client_id
    assert result.posts_tracked == 3
    assert result.total_impressions == 1000


async def test_summary_returns_404_for_wrong_client():
    from app.routers.analytics import client_analytics_summary
    from fastapi import HTTPException

    user_id = _user_id()
    other_user_id = _user_id()
    client_id = _client_id()
    client = _make_client(other_user_id, client_id)  # owned by different user

    request = MagicMock()
    db = AsyncMock()

    with (
        patch("app.routers.analytics.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc:
            await client_analytics_summary(
                request=request,
                client_id=client_id,
                current_user={"user_id": str(user_id)},
                db=db,
            )
    assert exc.value.status_code == 404


async def test_summary_returns_401_for_bad_session():
    from app.routers.analytics import client_analytics_summary
    from fastapi import HTTPException

    request = MagicMock()
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await client_analytics_summary(
            request=request,
            client_id=uuid.uuid4(),
            current_user={"bad": "payload"},
            db=db,
        )
    assert exc.value.status_code == 401


async def test_summary_empty_client_returns_zero_posts():
    from app.routers.analytics import client_analytics_summary
    from app.schemas.analytics import ClientSummaryResponse

    user_id = _user_id()
    client_id = _client_id()
    client = _make_client(user_id, client_id)

    empty_summary = ClientSummaryResponse(
        client_id=client_id,
        total_impressions=None,
        total_engagements=None,
        posts_tracked=0,
        best_post=None,
        freshest_captured_at=None,
    )

    request = MagicMock()
    db = AsyncMock()

    with (
        patch("app.routers.analytics.get_client", AsyncMock(return_value=client)),
        patch("app.routers.analytics.get_client_summary", AsyncMock(return_value=empty_summary)),
    ):
        result = await client_analytics_summary(
            request=request,
            client_id=client_id,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result.posts_tracked == 0
    assert result.total_impressions is None


# ---------------------------------------------------------------------------
# Posts endpoint tests
# ---------------------------------------------------------------------------

async def test_posts_returns_200_for_valid_client():
    from app.routers.analytics import client_post_metrics
    from app.schemas.analytics import ClientPostMetricsResponse, PostMetricItem

    user_id = _user_id()
    client_id = _client_id()
    client = _make_client(user_id, client_id)
    ppid = uuid.uuid4()

    mock_metrics = ClientPostMetricsResponse(
        client_id=client_id,
        items=[
            PostMetricItem(
                published_post_id=ppid,
                platform="instagram",
                campaign_title="Test campaign",
                campaign_excerpt=None,
                latest_impressions=500,
                latest_engagements=30,
                permalink="https://instagram.com/p/test",
                captured_at=None,
                series=[],
                unavailable_reason=None,
            )
        ],
        freshest_captured_at=None,
    )

    request = MagicMock()
    db = AsyncMock()

    with (
        patch("app.routers.analytics.get_client", AsyncMock(return_value=client)),
        patch("app.routers.analytics.get_client_post_metrics", AsyncMock(return_value=mock_metrics)),
    ):
        result = await client_post_metrics(
            request=request,
            client_id=client_id,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert len(result.items) == 1
    assert result.items[0].platform == "instagram"
    assert result.items[0].latest_impressions == 500


async def test_posts_unavailable_marker_returned():
    """Posts with no snapshots return explicit unavailable marker, not fabricated zeros."""
    from app.routers.analytics import client_post_metrics
    from app.schemas.analytics import ClientPostMetricsResponse, PostMetricItem

    user_id = _user_id()
    client_id = _client_id()
    client = _make_client(user_id, client_id)
    ppid = uuid.uuid4()

    mock_metrics = ClientPostMetricsResponse(
        client_id=client_id,
        items=[
            PostMetricItem(
                published_post_id=ppid,
                platform="facebook_page",
                campaign_title="FB campaign",
                campaign_excerpt=None,
                latest_impressions=None,
                latest_engagements=None,
                permalink=None,
                captured_at=None,
                series=[],
                unavailable_reason="facebook_under_100_likes",
            )
        ],
        freshest_captured_at=None,
    )

    request = MagicMock()
    db = AsyncMock()

    with (
        patch("app.routers.analytics.get_client", AsyncMock(return_value=client)),
        patch("app.routers.analytics.get_client_post_metrics", AsyncMock(return_value=mock_metrics)),
    ):
        result = await client_post_metrics(
            request=request,
            client_id=client_id,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    item = result.items[0]
    assert item.unavailable_reason == "facebook_under_100_likes"
    assert item.latest_impressions is None
    assert item.latest_engagements is None


async def test_posts_empty_client_returns_empty_list():
    from app.routers.analytics import client_post_metrics
    from app.schemas.analytics import ClientPostMetricsResponse

    user_id = _user_id()
    client_id = _client_id()
    client = _make_client(user_id, client_id)

    empty = ClientPostMetricsResponse(
        client_id=client_id,
        items=[],
        freshest_captured_at=None,
    )

    request = MagicMock()
    db = AsyncMock()

    with (
        patch("app.routers.analytics.get_client", AsyncMock(return_value=client)),
        patch("app.routers.analytics.get_client_post_metrics", AsyncMock(return_value=empty)),
    ):
        result = await client_post_metrics(
            request=request,
            client_id=client_id,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result.items == []


# ---------------------------------------------------------------------------
# Service-level rollup SQL correctness (unit tests via mocked session)
# ---------------------------------------------------------------------------

async def test_service_summary_empty_db_returns_zero():
    """get_client_summary must not 500 when post_metrics has no rows (AD-A10)."""
    from app.services.analytics import get_client_summary

    client_id = uuid.uuid4()
    session = AsyncMock()

    # Simulate DB returning a row with COUNT(*)=0
    mock_row = {"posts_tracked": 0, "total_impressions": None, "total_engagements": None, "freshest_captured_at": None, "best_post_id": None}
    mock_result = MagicMock()
    mock_result.mappings.return_value.first.return_value = mock_row
    session.execute = AsyncMock(return_value=mock_result)

    result = await get_client_summary(session, client_id)

    assert result.posts_tracked == 0
    assert result.total_impressions is None
    assert result.best_post is None


async def test_service_posts_empty_db_returns_empty_list():
    """get_client_post_metrics must not 500 and return empty list (AD-A10)."""
    from app.services.analytics import get_client_post_metrics

    client_id = uuid.uuid4()
    session = AsyncMock()

    # No published posts
    mock_posts_result = MagicMock()
    mock_posts_result.mappings.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=mock_posts_result)

    result = await get_client_post_metrics(session, client_id)

    assert result.items == []
    assert result.freshest_captured_at is None


async def test_service_posts_no_snapshot_marker():
    """Posts with no matching snapshot in post_metrics get unavailable_reason='no_snapshot'."""
    from app.services.analytics import get_client_post_metrics

    client_id = uuid.uuid4()
    ppid = uuid.uuid4()
    camp_id = uuid.uuid4()

    session = AsyncMock()
    calls = []

    def fake_execute(query, params=None):
        calls.append(params)
        result = MagicMock()
        call_n = len(calls)
        if call_n == 1:
            # published posts query
            post_row = {
                "published_post_id": ppid,
                "platform": "instagram",
                "permalink": None,
                "campaign_title": "Test brain dump text",
                "campaign_excerpt": None,
            }
            result.mappings.return_value.all.return_value = [post_row]
        elif call_n == 2:
            # latest_per_post query - no snapshot
            result.mappings.return_value.all.return_value = []
        elif call_n == 3:
            # series query - no data
            result.mappings.return_value.all.return_value = []
        elif call_n == 4:
            # MAX(captured_at) freshest query - no data
            result.scalar = MagicMock(return_value=None)
        return result

    session.execute = AsyncMock(side_effect=lambda q, p=None: fake_execute(q, p))

    result = await get_client_post_metrics(session, client_id)

    assert len(result.items) == 1
    item = result.items[0]
    assert item.unavailable_reason == "no_snapshot"
    assert item.latest_impressions is None
    assert item.latest_engagements is None
