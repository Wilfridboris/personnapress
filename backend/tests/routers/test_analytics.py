"""Tests for GET /api/v1/analytics/clients/{client_id}/summary and /posts.

Story 24.4 additions (AC #13):
  - engagement_rate field: NULL when impressions=0 or NULL (no divide-by-zero)
  - latest_likes/comments/shares in PostMetricItem
  - total_likes/comments/shares/engagement_rate in ClientSummaryResponse
  - reason-string alignment: unavailable_reason uses 'page_under_100_likes'
"""
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
        total_likes=30,
        total_comments=10,
        total_shares=5,
        engagement_rate=0.05,
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
    assert result.total_likes == 30
    assert result.total_comments == 10
    assert result.total_shares == 5
    assert result.engagement_rate == 0.05


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
        total_likes=None,
        total_comments=None,
        total_shares=None,
        engagement_rate=None,
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
    assert result.engagement_rate is None


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
                latest_likes=20,
                latest_comments=6,
                latest_shares=4,
                engagement_rate=0.06,
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
    item = result.items[0]
    assert item.platform == "instagram"
    assert item.latest_impressions == 500
    assert item.latest_likes == 20
    assert item.latest_comments == 6
    assert item.latest_shares == 4
    assert item.engagement_rate == 0.06


async def test_posts_unavailable_marker_returned():
    """Posts with no snapshots return explicit unavailable marker, not fabricated zeros.
    Story 24.4 AC#11: reason string uses 'page_under_100_likes' (not 'facebook_under_100_likes').
    """
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
                latest_likes=None,
                latest_comments=None,
                latest_shares=None,
                engagement_rate=None,
                permalink=None,
                captured_at=None,
                series=[],
                unavailable_reason="page_under_100_likes",
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
    assert item.unavailable_reason == "page_under_100_likes"
    assert item.latest_impressions is None
    assert item.latest_engagements is None
    assert item.latest_likes is None
    assert item.latest_comments is None
    assert item.latest_shares is None
    assert item.engagement_rate is None


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

    mock_row = {
        "posts_tracked": 0,
        "total_impressions": None,
        "total_engagements": None,
        "total_likes": None,
        "total_comments": None,
        "total_shares": None,
        "engagement_rate": None,
        "freshest_captured_at": None,
        "best_post_id": None,
    }
    mock_result = MagicMock()
    mock_result.mappings.return_value.first.return_value = mock_row
    session.execute = AsyncMock(return_value=mock_result)

    result = await get_client_summary(session, client_id)

    assert result.posts_tracked == 0
    assert result.total_impressions is None
    assert result.total_likes is None
    assert result.engagement_rate is None
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
    assert item.latest_likes is None
    assert item.latest_comments is None
    assert item.latest_shares is None
    assert item.engagement_rate is None


# ---------------------------------------------------------------------------
# 24.4 AC#13 — engagement_rate NULL-safety
# ---------------------------------------------------------------------------

async def test_service_posts_engagement_rate_null_when_impressions_zero():
    """engagement_rate must be NULL (not infinity/error) when impressions=0. (AC #5, #13)"""
    from app.services.analytics import get_client_post_metrics

    client_id = uuid.uuid4()
    ppid = uuid.uuid4()
    session = AsyncMock()
    calls = []

    def fake_execute(query, params=None):
        calls.append(params)
        result = MagicMock()
        call_n = len(calls)
        if call_n == 1:
            post_row = {
                "published_post_id": ppid,
                "platform": "threads",
                "permalink": None,
                "campaign_title": "Threads post",
                "campaign_excerpt": None,
            }
            result.mappings.return_value.all.return_value = [post_row]
        elif call_n == 2:
            # latest snapshot with impressions=0 -> engagement_rate must be NULL
            snap = {
                "published_post_id": ppid,
                "impressions": 0,
                "engagements": 5,
                "likes": 3,
                "comments": 1,
                "shares": 1,
                "engagement_rate": None,  # SQL NULLIF(0,0) -> NULL
                "captured_at": None,
                "unavailable_reason": None,
            }
            result.mappings.return_value.all.return_value = [snap]
        elif call_n == 3:
            result.mappings.return_value.all.return_value = []
        elif call_n == 4:
            result.scalar = MagicMock(return_value=None)
        return result

    session.execute = AsyncMock(side_effect=lambda q, p=None: fake_execute(q, p))

    result = await get_client_post_metrics(session, client_id)

    item = result.items[0]
    assert item.engagement_rate is None  # no divide-by-zero
    assert item.latest_engagements == 5
    assert item.latest_likes == 3


async def test_service_posts_engagement_rate_null_when_impressions_none():
    """engagement_rate must be NULL when impressions IS NULL (data not collected). (AC #5, #13)"""
    from app.services.analytics import get_client_post_metrics

    client_id = uuid.uuid4()
    ppid = uuid.uuid4()
    session = AsyncMock()
    calls = []

    def fake_execute(query, params=None):
        calls.append(params)
        result = MagicMock()
        call_n = len(calls)
        if call_n == 1:
            post_row = {
                "published_post_id": ppid,
                "platform": "instagram",
                "permalink": None,
                "campaign_title": "IG post",
                "campaign_excerpt": None,
            }
            result.mappings.return_value.all.return_value = [post_row]
        elif call_n == 2:
            snap = {
                "published_post_id": ppid,
                "impressions": None,
                "engagements": 10,
                "likes": 8,
                "comments": 2,
                "shares": 0,
                "engagement_rate": None,  # NULL impressions -> NULL rate
                "captured_at": None,
                "unavailable_reason": None,
            }
            result.mappings.return_value.all.return_value = [snap]
        elif call_n == 3:
            result.mappings.return_value.all.return_value = []
        elif call_n == 4:
            result.scalar = MagicMock(return_value=None)
        return result

    session.execute = AsyncMock(side_effect=lambda q, p=None: fake_execute(q, p))

    result = await get_client_post_metrics(session, client_id)

    item = result.items[0]
    assert item.engagement_rate is None  # NULL impressions -> NULL rate
    assert item.latest_engagements == 10
    assert item.latest_likes == 8
