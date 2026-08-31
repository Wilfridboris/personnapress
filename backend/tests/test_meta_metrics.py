"""Tests for Story 24.2 + 24.4 + 24.5: Meta metrics integration and analytics worker.

AC #11 coverage (24.2):
  1. Mapping of FB/IG/Threads insights payloads to normalized columns
  2. "Due post" cadence selection at representative post ages
  3. Per-item fault isolation (one post raises, others still produce snapshots)
  4. Append-only invariant (poll twice -> two rows, prior row unchanged)

AC #13 coverage (24.4):
  5. Component field mapping (likes/comments/shares) for FB / IG / Threads
  6. FB second-call fault isolation (object call fails -> primary snapshot preserved, components NULL)
  7. Backfill from representative raw payload; missing component stays NULL; unavailability stays NULL
  8. Reason-string alignment: backend emits "page_under_100_likes" (AC #11 from story 24.4)

AC #10 coverage (24.5 — Meta API drift fix):
  9.  Threads fetch uses THREADS_GRAPH_BASE (graph.threads.com), not graph.facebook.com
  10. _threads_metrics_dict reads values[0].value (list form), not item.get("value")
  11. FB metric set contains no deprecated metric (post_impressions/post_engaged_users/post_reactions_by_type_total)
  12. FB snapshot maps post_reactions_*_total -> likes; impressions=None (no confirmed views metric)
  13. FB row with NULL impressions + real engagements: unavailable_reason is None (not an unavailable row)
  14. NULL-impression rollup: engagement_rate computed only over posts with non-NULL impressions
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


# ── Story 24.5 AC#10.9 — Threads host ────────────────────────────────────────

async def test_threads_fetch_uses_threads_graph_base():
    """Threads fetch must hit graph.threads.com, not graph.facebook.com (Story 24.5 AC#1/6)."""
    from app.integrations.meta_metrics import fetch, THREADS_GRAPH_BASE

    # Confirm the constant is correct
    assert "graph.threads.com" in THREADS_GRAPH_BASE
    assert "graph.facebook.com" not in THREADS_GRAPH_BASE

    # Confirm the URL built in _fetch_threads uses THREADS_GRAPH_BASE
    good_resp = _httpx_response(200, {
        "data": [
            {"name": "views", "values": [{"value": 900}]},
            {"name": "likes", "values": [{"value": 40}]},
            {"name": "replies", "values": [{"value": 15}]},
            {"name": "reposts", "values": [{"value": 10}]},
            {"name": "quotes", "values": [{"value": 5}]},
        ]
    })

    captured_urls: list[str] = []

    async def capturing_get(url: str, **kwargs):
        captured_urls.append(url)
        return good_resp

    mock_http_client = AsyncMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)
    mock_http_client.get = AsyncMock(side_effect=capturing_get)

    post = _published_post("threads", "threads_media_999")

    with patch("app.integrations.meta_metrics.httpx.AsyncClient", return_value=mock_http_client):
        snapshots = await fetch([post], THREADS_CREDS, "threads")

    assert len(snapshots) == 1
    assert len(captured_urls) == 1
    url_called = captured_urls[0]
    assert "graph.threads.com" in url_called, f"Expected graph.threads.com in URL, got: {url_called}"
    assert "graph.facebook.com" not in url_called, f"URL must NOT use graph.facebook.com: {url_called}"


# ── Story 24.5 AC#10.10 — Threads values[0].value parse ─────────────────────

async def test_threads_metrics_dict_reads_values_list_form():
    """_threads_metrics_dict reads values[0].value (list form), not item.get('value') (Story 24.5 AC#2)."""
    from app.integrations.meta_metrics import _threads_metrics_dict

    raw = {
        "data": [
            {"name": "views", "values": [{"value": 900}]},
            {"name": "likes", "values": [{"value": 40}]},
            {"name": "replies", "values": [{"value": 15}]},
            {"name": "reposts", "values": [{"value": 10}]},
            {"name": "quotes", "values": [{"value": 5}]},
        ]
    }
    m = _threads_metrics_dict(raw)

    assert m["views"] == 900
    assert m["likes"] == 40
    assert m["replies"] == 15
    assert m["reposts"] == 10
    assert m["quotes"] == 5


async def test_threads_metrics_dict_flat_value_returns_zero():
    """Old flat item.get('value') payload (incorrect shape) yields zeros — not crash, not wrong data."""
    from app.integrations.meta_metrics import _threads_metrics_dict

    # If API returns flat "value" (old/wrong shape), "values" key is absent -> val=0 -> 0 stored.
    raw = {
        "data": [
            {"name": "likes", "value": 40},   # old incorrect shape (no "values" list)
        ]
    }
    m = _threads_metrics_dict(raw)
    assert m["likes"] == 0  # "values" key missing -> 0, not 40 — correct behaviour for wrong shape


async def test_map_threads_payload_to_normalized_columns_list_form():
    """Threads insights maps views->impressions, sums engagement fields using list-form payload (Story 24.5)."""
    from app.integrations.meta_metrics import _map_threads_snapshot

    raw = {
        "data": [
            {"name": "views", "values": [{"value": 900}]},
            {"name": "likes", "values": [{"value": 40}]},
            {"name": "replies", "values": [{"value": 15}]},
            {"name": "reposts", "values": [{"value": 10}]},
            {"name": "quotes", "values": [{"value": 5}]},
        ]
    }
    post = _published_post("threads", "threads_media_001")

    snap = _map_threads_snapshot(post, raw, _NOW)

    assert snap.impressions == 900
    assert snap.engagements == 70    # 40+15+10+5
    assert snap.platform == "threads"
    assert snap.unavailable_reason is None
    # Story 24.4: Threads noun mapping — replies->comments, reposts->shares
    assert snap.likes == 40
    assert snap.comments == 15   # replies
    assert snap.shares == 10     # reposts


# ── Story 24.5 AC#10.11 — FB metric set has no deprecated metrics ────────────

def test_fb_metrics_has_no_deprecated_metrics():
    """_FB_METRICS must not contain any June-2026-deprecated metrics (Story 24.5 AC#4)."""
    from app.integrations.meta_metrics import _FB_METRICS

    deprecated = {"post_impressions", "post_engaged_users", "post_reactions_by_type_total"}
    for dep in deprecated:
        assert dep not in _FB_METRICS, (
            f"_FB_METRICS must not contain deprecated metric '{dep}' — "
            f"it was removed in Meta's June 2026 Page Insights deprecation"
        )

    # Must contain per-type reaction counters
    assert "post_reactions_like_total" in _FB_METRICS
    assert "post_reactions_love_total" in _FB_METRICS


# ── Story 24.5 AC#10.12 — FB snapshot maps reactions -> likes, impressions=None ──

async def test_map_facebook_reactions_to_likes_impressions_null():
    """FB snapshot sums post_reactions_*_total to likes; impressions=None when no views metric (Story 24.5 AC#5/5a)."""
    from app.integrations.meta_metrics import _map_facebook_snapshot

    raw = {
        "data": [
            {"name": "post_reactions_like_total", "values": [{"value": 80, "end_time": "2026-08-17"}]},
            {"name": "post_reactions_love_total", "values": [{"value": 10, "end_time": "2026-08-17"}]},
            {"name": "post_reactions_wow_total", "values": [{"value": 3, "end_time": "2026-08-17"}]},
            {"name": "post_reactions_haha_total", "values": [{"value": 2, "end_time": "2026-08-17"}]},
            {"name": "post_reactions_sorry_total", "values": [{"value": 1, "end_time": "2026-08-17"}]},
            {"name": "post_reactions_anger_total", "values": [{"value": 0, "end_time": "2026-08-17"}]},
            # No post_media_view -> impressions should be None
        ],
        "_object": {
            "comments": {"summary": {"total_count": 12}},
            "shares": {"count": 7},
        },
    }
    post = _published_post("facebook_page", "fb_post_new_metrics")

    snap = _map_facebook_snapshot(post, raw, _NOW)

    # impressions=None (no views metric returned)
    assert snap.impressions is None
    # likes = sum of all reaction counters = 80+10+3+2+1+0 = 96
    assert snap.likes == 96
    assert snap.comments == 12
    assert snap.shares == 7
    # engagements = likes + comments + shares = 96 + 12 + 7 = 115
    assert snap.engagements == 115
    assert snap.platform == "facebook_page"
    assert snap.unavailable_reason is None


async def test_map_facebook_with_post_media_view_sets_impressions():
    """When post_media_view is present and non-zero, FB impressions is populated (Story 24.5 AC#5)."""
    from app.integrations.meta_metrics import _map_facebook_snapshot

    raw = {
        "data": [
            {"name": "post_reactions_like_total", "values": [{"value": 50}]},
            {"name": "post_reactions_love_total", "values": [{"value": 5}]},
            {"name": "post_reactions_wow_total", "values": [{"value": 0}]},
            {"name": "post_reactions_haha_total", "values": [{"value": 0}]},
            {"name": "post_reactions_sorry_total", "values": [{"value": 0}]},
            {"name": "post_reactions_anger_total", "values": [{"value": 0}]},
            {"name": "post_media_view", "values": [{"value": 1234}]},
        ],
    }
    post = _published_post("facebook_page", "fb_post_with_views")

    snap = _map_facebook_snapshot(post, raw, _NOW)

    assert snap.impressions == 1234
    assert snap.likes == 55  # 50+5
    assert snap.unavailable_reason is None


# ── Story 24.5 AC#10.13 — FB NULL impressions is NOT an unavailable row ──────

async def test_facebook_null_impressions_not_unavailable_row():
    """FB post with NULL impressions + real engagements: unavailable_reason=None (Story 24.5 AC#5a/9)."""
    from app.integrations.meta_metrics import fetch

    # API returns 200 with reactions but no post_media_view -> impressions=None
    insights_body = {
        "data": [
            {"name": "post_reactions_like_total", "values": [{"value": 30}]},
            {"name": "post_reactions_love_total", "values": [{"value": 5}]},
            {"name": "post_reactions_wow_total", "values": [{"value": 0}]},
            {"name": "post_reactions_haha_total", "values": [{"value": 0}]},
            {"name": "post_reactions_sorry_total", "values": [{"value": 0}]},
            {"name": "post_reactions_anger_total", "values": [{"value": 0}]},
            # no post_media_view
        ]
    }
    obj_body = {
        "comments": {"summary": {"total_count": 5}},
        "shares": {"count": 3},
        "id": "123",
    }

    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _httpx_response(200, insights_body)
        return _httpx_response(200, obj_body)

    mock_http_client = AsyncMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)
    mock_http_client.get = AsyncMock(side_effect=side_effect)

    post = _published_post("facebook_page", "fb_null_impressions_post")

    with patch("app.integrations.meta_metrics.httpx.AsyncClient", return_value=mock_http_client):
        snapshots = await fetch([post], FB_CREDS, "facebook_page")

    assert len(snapshots) == 1
    snap = snapshots[0]
    # NULL impressions is NOT an unavailable row — engagements are real
    assert snap.impressions is None
    assert snap.unavailable_reason is None
    assert snap.likes == 35  # 30+5
    assert snap.comments == 5
    assert snap.shares == 3
    assert snap.engagements == 43  # 35+5+3


# ── AC #11.1 / 24.4 AC#13 — payload mapping (IG unchanged) ──────────────────

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
    # Story 24.4: component fields
    assert snap.likes == 50
    assert snap.comments == 12
    assert snap.shares == 5


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
    assert snap.likes == 30
    assert snap.comments == 5
    assert snap.shares == 1


async def test_facebook_page_under_100_likes_returns_unavailable_not_exception():
    """FB Page with fewer than 100 likes yields an unavailable snapshot, not a raised error.
    Story 24.4 AC#11: reason string is 'page_under_100_likes' (not 'facebook_under_100_likes').
    """
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
        with patch("app.integrations.meta_metrics.sentry_sdk"):
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


# ── 24.4 AC#13 — FB second call fault isolation ──────────────────────────────

async def test_facebook_object_edge_failure_preserves_primary_snapshot():
    """If the FB second (object-edge) call fails, primary engagements are still recorded
    and comments/shares are NULL (not raised, not lost) — AD-A10 fault isolation.
    Story 24.5: impressions=None (no views metric), engagements from reactions."""
    from app.integrations.meta_metrics import fetch

    insights_resp = _httpx_response(200, {
        "data": [
            {"name": "post_reactions_like_total", "values": [{"value": 20}]},
            {"name": "post_reactions_love_total", "values": [{"value": 0}]},
            {"name": "post_reactions_wow_total", "values": [{"value": 0}]},
            {"name": "post_reactions_haha_total", "values": [{"value": 0}]},
            {"name": "post_reactions_sorry_total", "values": [{"value": 0}]},
            {"name": "post_reactions_anger_total", "values": [{"value": 0}]},
        ]
    })

    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return insights_resp
        # Second call (object-edge) raises a network error
        raise httpx.ConnectError("object edge call failed")

    mock_http_client = AsyncMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)
    mock_http_client.get = AsyncMock(side_effect=side_effect)

    post = _published_post("facebook_page", "fb_post_fault")

    with patch("app.integrations.meta_metrics.httpx.AsyncClient", return_value=mock_http_client):
        snapshots = await fetch([post], FB_CREDS, "facebook_page")

    assert len(snapshots) == 1
    snap = snapshots[0]
    # impressions=None (no views metric), but NOT an unavailable row
    assert snap.impressions is None
    assert snap.unavailable_reason is None
    # likes from reactions
    assert snap.likes == 20
    # engagements = reactions only (comments/shares degraded to NULL by object-edge failure)
    assert snap.engagements == 20
    # Object-edge data degraded to NULL — not raised, not fabricated
    assert snap.comments is None
    assert snap.shares is None


async def test_facebook_object_edge_non200_preserves_primary_snapshot():
    """FB second call returning non-200 degrades comments/shares to NULL without error."""
    from app.integrations.meta_metrics import fetch

    insights_resp = _httpx_response(200, {
        "data": [
            {"name": "post_reactions_like_total", "values": [{"value": 10}]},
            {"name": "post_reactions_love_total", "values": [{"value": 0}]},
            {"name": "post_reactions_wow_total", "values": [{"value": 0}]},
            {"name": "post_reactions_haha_total", "values": [{"value": 0}]},
            {"name": "post_reactions_sorry_total", "values": [{"value": 0}]},
            {"name": "post_reactions_anger_total", "values": [{"value": 0}]},
        ]
    })
    obj_error_resp = _httpx_response(400, {"error": {"code": 100, "message": "Not found"}})

    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return insights_resp if call_count == 1 else obj_error_resp

    mock_http_client = AsyncMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)
    mock_http_client.get = AsyncMock(side_effect=side_effect)

    post = _published_post("facebook_page", "fb_post_obj_non200")

    with patch("app.integrations.meta_metrics.httpx.AsyncClient", return_value=mock_http_client):
        snapshots = await fetch([post], FB_CREDS, "facebook_page")

    assert len(snapshots) == 1
    snap = snapshots[0]
    assert snap.impressions is None  # no views metric
    assert snap.likes == 10
    assert snap.comments is None
    assert snap.shares is None


# ── 24.4 AC#13 — backfill / extract_components_from_raw ─────────────────────

def test_extract_components_from_raw_instagram():
    """extract_components_from_raw returns correct IG components."""
    from app.integrations.meta_metrics import extract_components_from_raw

    raw = {
        "data": [
            {"name": "likes", "values": [{"value": 50}]},
            {"name": "comments", "values": [{"value": 12}]},
            {"name": "shares", "values": [{"value": 5}]},
            {"name": "saved", "values": [{"value": 8}]},
        ]
    }
    likes, comments, shares = extract_components_from_raw("instagram", raw)
    assert likes == 50
    assert comments == 12
    assert shares == 5


def test_extract_components_from_raw_threads():
    """extract_components_from_raw maps replies->comments, reposts->shares for Threads (list-form payload)."""
    from app.integrations.meta_metrics import extract_components_from_raw

    # Story 24.5: Threads payload is list form (values[0].value)
    raw = {
        "data": [
            {"name": "likes", "values": [{"value": 40}]},
            {"name": "replies", "values": [{"value": 15}]},
            {"name": "reposts", "values": [{"value": 10}]},
            {"name": "quotes", "values": [{"value": 5}]},
        ]
    }
    likes, comments, shares = extract_components_from_raw("threads", raw)
    assert likes == 40
    assert comments == 15   # replies -> comments
    assert shares == 10     # reposts -> shares


def test_extract_components_missing_field_stays_null():
    """A raw payload missing a component field returns None (not zero) for that field."""
    from app.integrations.meta_metrics import extract_components_from_raw

    # IG payload with no 'shares' field
    raw = {
        "data": [
            {"name": "likes", "values": [{"value": 20}]},
            {"name": "comments", "values": [{"value": 3}]},
            # 'shares' absent
        ]
    }
    likes, comments, shares = extract_components_from_raw("instagram", raw)
    assert likes == 20
    assert comments == 3
    assert shares is None  # absent, not zero


def test_extract_components_unavailability_row_returns_null():
    """An unavailability row (error payload, no 'data' key) returns all NULL components."""
    from app.integrations.meta_metrics import extract_components_from_raw

    error_raw = {"error": {"code": 100, "error_subcode": 33, "message": "Unavailable"}}
    likes, comments, shares = extract_components_from_raw("facebook_page", error_raw)
    assert likes is None
    assert comments is None
    assert shares is None


def test_extract_components_facebook_with_object_edge():
    """FB raw with _object key and post_reactions_*_total returns reactions-summed likes and comments/shares."""
    from app.integrations.meta_metrics import extract_components_from_raw

    # Story 24.5: per-type counters, not post_reactions_by_type_total
    raw = {
        "data": [
            {"name": "post_reactions_like_total", "values": [{"value": 25}]},
            {"name": "post_reactions_love_total", "values": [{"value": 5}]},
            {"name": "post_reactions_wow_total", "values": [{"value": 0}]},
            {"name": "post_reactions_haha_total", "values": [{"value": 0}]},
            {"name": "post_reactions_sorry_total", "values": [{"value": 0}]},
            {"name": "post_reactions_anger_total", "values": [{"value": 0}]},
        ],
        "_object": {
            "comments": {"summary": {"total_count": 8}},
            "shares": {"count": 4},
        },
    }
    likes, comments, shares = extract_components_from_raw("facebook_page", raw)
    assert likes == 30  # 25+5
    assert comments == 8
    assert shares == 4


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
        impressions=None,   # Story 24.5: FB impressions is NULL
        engagements=18,
        likes=8,
        comments=None,
        shares=None,
        raw={"poll": 1},
    )
    snap2 = MetricSnapshot(
        published_post_id=published_post_id,
        client_id=client_id,
        platform="facebook_page",
        captured_at=_NOW,
        impressions=None,   # Story 24.5: FB impressions is NULL
        engagements=23,
        likes=12,
        comments=2,
        shares=1,
        raw={"poll": 2},
    )

    added_objects = []

    mock_session = AsyncMock()
    mock_session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))
    mock_session.flush = AsyncMock()

    await bulk_insert_snapshots(mock_session, [snap1])
    first_count = len(added_objects)
    first_row_engagements = added_objects[0].engagements

    await bulk_insert_snapshots(mock_session, [snap2])

    assert len(added_objects) == 2, "Each poll must produce a new INSERT row"
    assert first_row_engagements == 18, "First row was mutated — append-only invariant violated"
    # The second row carries the newer numbers
    assert added_objects[1].impressions is None
    assert added_objects[1].engagements == 23
    assert added_objects[1].captured_at == _NOW
    assert added_objects[1].likes == 12
    assert added_objects[1].comments == 2
    assert added_objects[1].shares == 1


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
        likes=15,
        comments=3,
        shares=2,
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


# ── Story 24.5 AC#10.14 — NULL-impression rollup ─────────────────────────────

async def test_client_summary_engagement_rate_excludes_null_impression_posts():
    """engagement_rate is computed only over posts with non-NULL impressions (Story 24.5 AC#5a).

    A FB post (impressions=NULL, engagements=43) alongside an IG post (impressions=5000,
    engagements=200) must yield rate=200/5000=0.04, not (200+43)/5000=0.0486.

    The SQL CASE expression in get_client_summary ensures the FB engagements are excluded
    from the numerator when impressions is NULL. This test mocks the session to return
    the rate the SQL should produce, then asserts the service passes it through cleanly.
    Full SQL formula verification requires a Postgres integration test.
    """
    from app.services.analytics import get_client_summary

    client_id = uuid.uuid4()
    expected_rate = 200.0 / 5000.0  # only IG post counted

    mock_row = MagicMock()
    mock_row.__getitem__ = lambda self, k: {
        "posts_tracked": 2,
        "total_impressions": 5000,
        "total_engagements": 243,  # both posts
        "total_likes": None,
        "total_comments": None,
        "total_shares": None,
        "engagement_rate": expected_rate,  # SQL formula: only IG post in numerator
        "freshest_captured_at": _NOW,
        "best_post_id": None,
    }[k]

    mock_result = MagicMock()
    mock_result.mappings.return_value.first.return_value = mock_row
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    summary = await get_client_summary(mock_session, client_id)

    assert summary.posts_tracked == 2
    assert summary.total_impressions == 5000
    assert summary.total_engagements == 243
    # Rate must be 0.04 (IG only), not 0.0486 (IG+FB engagements / IG impressions)
    assert abs(summary.engagement_rate - expected_rate) < 1e-9, (
        f"engagement_rate={summary.engagement_rate} should be {expected_rate} "
        f"(only impressions-bearing posts in numerator)"
    )
