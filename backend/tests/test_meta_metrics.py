"""Tests for Story 24.2: Meta metrics integration and analytics worker.

AC #11 coverage:
  1. Mapping of FB/IG/Threads insights payloads to normalized columns
  2. "Due post" cadence selection at representative post ages
  3. Per-item fault isolation (one post raises, others still produce snapshots)
  4. Append-only invariant (poll twice -> two rows, prior row unchanged)
"""
import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _published_post(platform: str, platform_post_id: str = "post_123") -> MagicMock:
    pp = MagicMock()
    pp.id = uuid.uuid4()
    pp.client_id = uuid.uuid4()
    pp.platform = platform
    pp.platform_post_id = platform_post_id
    return pp


def _httpx_response(status_code: int, body: dict) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        content=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
    )


_NOW = datetime(2026, 8, 17, 12, 0, 0, tzinfo=timezone.utc)

FB_CREDS = {"page_access_token": "tok_fb"}
IG_CREDS = {"page_access_token": "tok_ig"}
THREADS_CREDS = {"user_access_token": "tok_threads"}


# ── AC #11.1 — payload mapping ────────────────────────────────────────────────

async def test_map_facebook_payload_to_normalized_columns():
    """FB insights payload maps impressions and engagements correctly."""
    from app.integrations.meta_metrics import _map_facebook_snapshot

    raw = {
        "data": [
            {"name": "post_impressions", "values": [{"value": 1500, "end_time": "2026-08-17"}]},
            {"name": "post_engaged_users", "values": [{"value": 120, "end_time": "2026-08-17"}]},
            {"name": "post_reactions_by_type_total", "values": [{"value": {"LIKE": 80, "LOVE": 10}, "end_time": "2026-08-17"}]},
        ]
    }
    post = _published_post("facebook_page", "fb_post_001")

    snap = _map_facebook_snapshot(post, raw, _NOW)

    assert snap.impressions == 1500
    assert snap.engagements == 120
    assert snap.platform == "facebook_page"
    assert snap.unavailable_reason is None
    assert snap.captured_at == _NOW


async def test_map_instagram_payload_uses_views_for_impressions():
    """IG insights maps `views` into impressions (impressions removed in Graph v21)."""
    from app.integrations.meta_metrics import _map_instagram_snapshot

    raw = {
        "data": [
            {"name": "views", "values": [{"value": 2000}]},
            {"name": "reach", "values": [{"value": 1800}]},
            {"name": "likes", "values": [{"value": 50}]},
            {"name": "comments", "values": [{"value": 12}]},
            {"name": "saved", "values": [{"value": 8}]},
            {"name": "shares", "values": [{"value": 5}]},
        ]
    }
    post = _published_post("instagram", "ig_media_001")

    snap = _map_instagram_snapshot(post, raw, _NOW)

    assert snap.impressions == 2000  # views, not reach
    assert snap.engagements == 75    # 50+12+8+5
    assert snap.platform == "instagram"
    assert snap.unavailable_reason is None


async def test_map_instagram_falls_back_to_reach_when_views_absent():
    """IG insights falls back to `reach` when `views` is missing."""
    from app.integrations.meta_metrics import _map_instagram_snapshot

    raw = {
        "data": [
            {"name": "reach", "values": [{"value": 1200}]},
            {"name": "likes", "values": [{"value": 30}]},
            {"name": "comments", "values": [{"value": 5}]},
            {"name": "saved", "values": [{"value": 2}]},
            {"name": "shares", "values": [{"value": 1}]},
        ]
    }
    post = _published_post("instagram")

    snap = _map_instagram_snapshot(post, raw, _NOW)

    assert snap.impressions == 1200
    assert snap.engagements == 38


async def test_map_threads_payload_to_normalized_columns():
    """Threads insights maps views->impressions and sums engagement fields."""
    from app.integrations.meta_metrics import _map_threads_snapshot

    raw = {
        "data": [
            {"name": "views", "value": 900},
            {"name": "likes", "value": 40},
            {"name": "replies", "value": 15},
            {"name": "reposts", "value": 10},
            {"name": "quotes", "value": 5},
        ]
    }
    post = _published_post("threads", "threads_media_001")

    snap = _map_threads_snapshot(post, raw, _NOW)

    assert snap.impressions == 900
    assert snap.engagements == 70    # 40+15+10+5
    assert snap.platform == "threads"
    assert snap.unavailable_reason is None


async def test_facebook_page_under_100_likes_returns_unavailable_not_exception():
    """FB Page with fewer than 100 likes yields an unavailable snapshot, not a raised error."""
    from app.integrations.meta_metrics import fetch

    error_body = {
        "error": {
            "message": "Unsupported operation on call to this endpoint.",
            "type": "OAuthException",
            "code": 100,
            "error_subcode": 33,
        }
    }
    mock_resp = _httpx_response(400, error_body)

    mock_http_client = AsyncMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)
    mock_http_client.get = AsyncMock(return_value=mock_resp)

    post = _published_post("facebook_page", "fb_small_page_post")

    with patch("app.integrations.meta_metrics.httpx.AsyncClient", return_value=mock_http_client):
        snapshots = await fetch([post], FB_CREDS, "facebook_page")

    assert len(snapshots) == 1
    snap = snapshots[0]
    assert snap.unavailable_reason == "page_under_100_likes"
    assert snap.impressions is None
    assert snap.engagements is None


async def test_instagram_permission_missing_returns_unavailable():
    """IG fetch with missing permission returns unavailable_reason=permission_missing."""
    from app.integrations.meta_metrics import fetch

    error_body = {"error": {"code": 10, "message": "Permission not granted"}}
    mock_resp = _httpx_response(400, error_body)

    mock_http_client = AsyncMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)
    mock_http_client.get = AsyncMock(return_value=mock_resp)

    post = _published_post("instagram")

    with patch("app.integrations.meta_metrics.httpx.AsyncClient", return_value=mock_http_client):
        snapshots = await fetch([post], IG_CREDS, "instagram")

    assert len(snapshots) == 1
    assert snapshots[0].unavailable_reason == "permission_missing"


async def test_threads_permission_missing_returns_unavailable():
    """Threads fetch with missing permission returns unavailable_reason=permission_missing."""
    from app.integrations.meta_metrics import fetch

    error_body = {"error": {"code": 10, "message": "Permission not granted"}}
    mock_resp = _httpx_response(400, error_body)

    mock_http_client = AsyncMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)
    mock_http_client.get = AsyncMock(return_value=mock_resp)

    post = _published_post("threads")

    with patch("app.integrations.meta_metrics.httpx.AsyncClient", return_value=mock_http_client):
        snapshots = await fetch([post], THREADS_CREDS, "threads")

    assert len(snapshots) == 1
    assert snapshots[0].unavailable_reason == "permission_missing"
    assert snapshots[0].impressions is None
    assert snapshots[0].engagements is None


# ── AC #11.2 — cadence selection ─────────────────────────────────────────────

@pytest.mark.parametrize("age_hours,last_poll_offset_hours,expected_due", [
    # Under 24 h: due every 1 h → due if last_poll >= 1 h ago
    (6,  0.5, False),   # 6 h old post, polled 30 min ago → not due yet
    (6,  1.5, True),    # 6 h old, polled 90 min ago → due (hourly cadence)
    (6,  None, True),   # 6 h old, never polled → due
    # 1-7 days: due daily
    (50, 20,  False),   # 50 h old, polled 20 h ago → not due
    (50, 25,  True),    # 50 h old, polled 25 h ago → due (daily cadence)
    (50, None, True),   # 50 h old, never polled → due
    # 7-90 days: due weekly
    (200, 160, False),  # 200 h old, polled 160 h ago → not due
    (200, 170, True),   # 200 h old, polled 170 h ago → due (weekly cadence = 168 h)
    # Beyond 90 days: never due
    (2200, None, False),  # 91+ days old → not due
])
def test_is_due_cadence(age_hours, last_poll_offset_hours, expected_due):
    """is_due() returns correct due status across all cadence buckets."""
    from app.workers.analytics import is_due

    now = _NOW
    published_at = now - timedelta(hours=age_hours)
    last_captured_at = (
        now - timedelta(hours=last_poll_offset_hours)
        if last_poll_offset_hours is not None
        else None
    )

    assert is_due(published_at, last_captured_at, now) is expected_due


def test_is_due_never_due_past_90_days():
    """Posts older than 90 days are never due regardless of last_captured_at."""
    from app.workers.analytics import is_due

    now = _NOW
    published_at = now - timedelta(days=91)
    # Even if never polled, beyond 90-day horizon → not due
    assert is_due(published_at, None, now) is False


# ── AC #11.3 — per-item fault isolation ──────────────────────────────────────

async def test_fetch_continues_after_one_post_raises():
    """If one post's HTTP call raises, the integration skips it and returns snapshots for others."""
    from app.integrations.meta_metrics import fetch

    good_resp = _httpx_response(200, {
        "data": [
            {"name": "views", "values": [{"value": 500}]},
            {"name": "likes", "values": [{"value": 20}]},
            {"name": "comments", "values": [{"value": 3}]},
            {"name": "saved", "values": [{"value": 1}]},
            {"name": "shares", "values": [{"value": 0}]},
        ]
    })

    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.ConnectError("network failure")
        return good_resp

    mock_http_client = AsyncMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)
    mock_http_client.get = AsyncMock(side_effect=side_effect)

    bad_post = _published_post("instagram", "ig_bad_001")
    good_post = _published_post("instagram", "ig_good_002")

    with patch("app.integrations.meta_metrics.httpx.AsyncClient", return_value=mock_http_client):
        with patch("app.integrations.meta_metrics.sentry_sdk") as mock_sentry:
            snapshots = await fetch([bad_post, good_post], IG_CREDS, "instagram")

    # Only the good post produces a snapshot; bad post is skipped
    assert len(snapshots) == 1
    assert snapshots[0].published_post_id == good_post.id
    # Sentry was called once for the network error
    mock_sentry.capture_exception.assert_called_once()


# ── AC #11.4 — append-only invariant ─────────────────────────────────────────

async def test_bulk_insert_writes_two_rows_on_two_polls():
    """Polling twice inserts two rows; the first row is never updated."""
    from app.integrations.meta_metrics import MetricSnapshot
    from app.db.repositories.post_metrics import bulk_insert_snapshots

    published_post_id = uuid.uuid4()
    client_id = uuid.uuid4()

    snap1 = MetricSnapshot(
        published_post_id=published_post_id,
        client_id=client_id,
        platform="facebook_page",
        captured_at=_NOW - timedelta(hours=2),
        impressions=100,
        engagements=10,
        raw={"poll": 1},
    )
    snap2 = MetricSnapshot(
        published_post_id=published_post_id,
        client_id=client_id,
        platform="facebook_page",
        captured_at=_NOW,
        impressions=150,
        engagements=15,
        raw={"poll": 2},
    )

    added_objects = []

    mock_session = AsyncMock()
    mock_session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))
    mock_session.flush = AsyncMock()

    await bulk_insert_snapshots(mock_session, [snap1])
    first_count = len(added_objects)
    first_row_impressions = added_objects[0].impressions

    await bulk_insert_snapshots(mock_session, [snap2])

    assert len(added_objects) == 2, "Each poll must produce a new INSERT row"
    assert first_row_impressions == 100, "First row was mutated — append-only invariant violated"
    # The second row carries the newer numbers
    assert added_objects[1].impressions == 150
    assert added_objects[1].captured_at == _NOW


async def test_bulk_insert_does_not_update_existing_row():
    """bulk_insert_snapshots only calls session.add(), never session.execute() with UPDATE."""
    from app.integrations.meta_metrics import MetricSnapshot
    from app.db.repositories.post_metrics import bulk_insert_snapshots

    snap = MetricSnapshot(
        published_post_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        platform="instagram",
        captured_at=_NOW,
        impressions=200,
        engagements=20,
        raw={},
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    await bulk_insert_snapshots(mock_session, [snap])

    mock_session.add.assert_called_once()
    # No UPDATE was issued via execute()
    for call_args in mock_session.execute.call_args_list:
        sql_str = str(call_args[0][0]).upper() if call_args[0] else ""
        assert "UPDATE" not in sql_str, "bulk_insert_snapshots must not issue UPDATE statements"
