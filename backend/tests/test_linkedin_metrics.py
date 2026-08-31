"""Tests for Story 25.1: LinkedIn company-page analytics integration.

AC #11 coverage:
  1.  test_map_snapshot_org_stats_payload       — sample organizationalEntityShareStatistics
                                                   response -> correct impressions/engagements/
                                                   likes/comments/shares
  2.  test_fetch_one_org_post_calls_per_post_stats  — share URN routes to per-post query
                                                       (URL has shares= param)
  3.  test_fetch_one_ugcpost_falls_back_to_aggregate — ugcPost URN routes to aggregate
                                                        (no shares= param)
  4.  test_fetch_one_personal_target_returns_member_unsupported — target=personal -> unavailable
  5.  test_fetch_one_401_returns_token_expired  — 401 -> token_expired
  6.  test_fetch_one_403_returns_scope_missing  — 403 -> scope_missing
  7.  test_fetch_one_no_elements_returns_no_data_yet — empty elements -> no_data_yet
  8.  test_fetch_fault_isolation                — one post raises, other posts still snapshot
  9.  test_capture_linkedin_post_wired_in_dispatch — publishing.py calls upsert_published_post
                                                      for linkedin after publish (mock)
  10. test_read_path_includes_linkedin          — _METRICS_PLATFORMS in analytics.py includes
                                                  "linkedin"
"""
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# ── Shared helpers ────────────────────────────────────────────────────────────

def _published_post(
    platform_post_id: str = "urn:li:share:7214567890123456789",
    target: str = "organization",
) -> MagicMock:
    pp = MagicMock()
    pp.id = uuid.uuid4()
    pp.client_id = uuid.uuid4()
    pp.platform = "linkedin"
    pp.platform_post_id = platform_post_id
    return pp


def _httpx_response(status_code: int, body: dict) -> httpx.Response:
    """Build an httpx.Response with a request attached so raise_for_status() works correctly."""
    request = httpx.Request("GET", "https://api.linkedin.com/rest/organizationalEntityShareStatistics")
    return httpx.Response(
        status_code=status_code,
        content=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
        request=request,
    )


_NOW = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

_ORG_CREDS = {
    "access_token": "tok_org",
    "org_id": "12345678",
    "target": "organization",
    "scopes": "r_organization_social,rw_organization_admin",
}

_PERSONAL_CREDS = {
    "access_token": "tok_personal",
    "org_id": None,
    "target": "personal",
    "scopes": "r_liteprofile",
}

# A representative organizationalEntityShareStatistics response
_SAMPLE_ORG_STATS = {
    "elements": [
        {
            "totalShareStatistics": {
                "impressionCount": 1500,
                "uniqueImpressionsCount": 1200,
                "likeCount": 45,
                "commentCount": 12,
                "shareCount": 8,
                "clickCount": 77,
                "engagement": 0.0952,
            }
        }
    ]
}


# ── 1. Snapshot mapping ───────────────────────────────────────────────────────

def test_map_snapshot_org_stats_payload():
    """A sample organizationalEntityShareStatistics payload maps to correct normalized columns."""
    from app.integrations.linkedin_metrics import _map_snapshot

    post = _published_post()
    snap = _map_snapshot(post, _SAMPLE_ORG_STATS, _NOW)

    assert snap.impressions == 1500            # impressionCount
    assert snap.likes == 45                    # likeCount
    assert snap.comments == 12                 # commentCount
    assert snap.shares == 8                    # shareCount
    # engagements = likes + comments + shares + clicks = 45+12+8+77 = 142
    assert snap.engagements == 142
    assert snap.unavailable_reason is None
    assert snap.platform == "linkedin"
    assert snap.raw == _SAMPLE_ORG_STATS


def test_map_snapshot_fallback_to_unique_impressions():
    """impressionCount absent -> fall back to uniqueImpressionsCount."""
    from app.integrations.linkedin_metrics import _map_snapshot

    raw = {
        "elements": [
            {
                "totalShareStatistics": {
                    "uniqueImpressionsCount": 900,
                    "likeCount": 10,
                    "commentCount": 2,
                    "shareCount": 1,
                    "clickCount": 5,
                }
            }
        ]
    }
    post = _published_post()
    snap = _map_snapshot(post, raw, _NOW)
    assert snap.impressions == 900
    assert snap.engagements == 18   # 10+2+1+5


def test_map_snapshot_no_data_yields_none_not_zero():
    """All stat fields absent -> None, not fabricated zeros (AD-A5)."""
    from app.integrations.linkedin_metrics import _map_snapshot

    raw = {"elements": [{"totalShareStatistics": {}}]}
    post = _published_post()
    snap = _map_snapshot(post, raw, _NOW)
    assert snap.impressions is None
    assert snap.engagements is None
    assert snap.likes is None
    assert snap.comments is None
    assert snap.shares is None


# ── 2. Share URN routes to per-post stats ─────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_one_org_post_calls_per_post_stats():
    """share URN -> per-post stats with shares= param in the URL."""
    from app.integrations.linkedin_metrics import _fetch_one

    share_urn = "urn:li:share:7214567890123456789"
    post = _published_post(platform_post_id=share_urn)

    captured_urls: list[str] = []
    captured_params: list[dict] = []

    async def fake_get(url, params=None, headers=None, **kwargs):
        captured_urls.append(url)
        captured_params.append(dict(params or {}))
        return _httpx_response(200, _SAMPLE_ORG_STATS)

    client = MagicMock()
    client.get = AsyncMock(side_effect=fake_get)

    snap = await _fetch_one(client, post, _ORG_CREDS, _NOW)

    assert snap.unavailable_reason is None
    assert any("organizationalEntityShareStatistics" in u for u in captured_urls)
    # After URL-encoding fix, shares=List() is embedded in the URL string (not the params dict).
    assert any("shares=List(" in u for u in captured_urls), (
        "Per-post stats call should include shares=List() in the URL for share URN"
    )


# ── 3. ugcPost URN falls back to aggregate (no shares= param) ─────────────────

@pytest.mark.asyncio
async def test_fetch_one_ugcpost_falls_back_to_aggregate():
    """ugcPost URN -> org-aggregate stats (no shares= in the URL sent)."""
    from app.integrations.linkedin_metrics import _fetch_one

    ugc_urn = "urn:li:ugcPost:9876543210987654321"
    post = _published_post(platform_post_id=ugc_urn)

    captured_urls: list[str] = []

    async def fake_get(url, params=None, headers=None, **kwargs):
        captured_urls.append(url)
        return _httpx_response(200, _SAMPLE_ORG_STATS)

    client = MagicMock()
    client.get = AsyncMock(side_effect=fake_get)

    snap = await _fetch_one(client, post, _ORG_CREDS, _NOW)

    assert snap.unavailable_reason is None
    # After URL-encoding fix, shares= would appear in the URL for per-post stats.
    # Aggregate path must not include it.
    assert all("shares" not in u for u in captured_urls), (
        "Aggregate call should not include shares= in the URL for ugcPost URN"
    )


# ── 4. Personal target with flag OFF -> member_metrics_disabled (Story 25.2) ──

@pytest.mark.asyncio
async def test_fetch_one_personal_target_flag_off_returns_member_disabled():
    """target=personal + LINKEDIN_MEMBER_METRICS_ENABLED False -> member_metrics_disabled, no API call."""
    from app.integrations.linkedin_metrics import _fetch_one

    post = _published_post()
    client = MagicMock()
    client.get = AsyncMock()  # should never be called

    with patch("app.integrations.linkedin_metrics.settings.LINKEDIN_MEMBER_METRICS_ENABLED", False):
        snap = await _fetch_one(client, post, _PERSONAL_CREDS, _NOW)

    assert snap.unavailable_reason == "member_metrics_disabled"
    assert snap.impressions is None
    assert snap.engagements is None
    client.get.assert_not_called()


# ── 5. 401 -> token_expired ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_one_401_returns_token_expired():
    """401 response -> unavailable_reason=token_expired."""
    from app.integrations.linkedin_metrics import _fetch_one

    post = _published_post()

    async def fake_get(url, params=None, headers=None, **kwargs):
        return _httpx_response(401, {"message": "Unauthorized"})

    client = MagicMock()
    client.get = AsyncMock(side_effect=fake_get)

    snap = await _fetch_one(client, post, _ORG_CREDS, _NOW)

    assert snap.unavailable_reason == "token_expired"
    assert snap.impressions is None


# ── 6. 403 -> scope_missing ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_one_403_returns_scope_missing():
    """403 response -> unavailable_reason=scope_missing."""
    from app.integrations.linkedin_metrics import _fetch_one

    post = _published_post()

    async def fake_get(url, params=None, headers=None, **kwargs):
        return _httpx_response(403, {"message": "Insufficient permissions"})

    client = MagicMock()
    client.get = AsyncMock(side_effect=fake_get)

    snap = await _fetch_one(client, post, _ORG_CREDS, _NOW)

    assert snap.unavailable_reason == "scope_missing"
    assert snap.impressions is None


# ── 7. Empty elements -> no_data_yet ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_one_no_elements_returns_no_data_yet():
    """200 with empty elements list -> unavailable_reason=no_data_yet."""
    from app.integrations.linkedin_metrics import _fetch_one

    post = _published_post()

    async def fake_get(url, params=None, headers=None, **kwargs):
        return _httpx_response(200, {"elements": []})

    client = MagicMock()
    client.get = AsyncMock(side_effect=fake_get)

    snap = await _fetch_one(client, post, _ORG_CREDS, _NOW)

    assert snap.unavailable_reason == "no_data_yet"
    assert snap.impressions is None


# ── 8. Fault isolation ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_fault_isolation():
    """One post raises an unhandled exception; other posts still produce snapshots."""
    from app.integrations.linkedin_metrics import fetch

    posts = [
        _published_post(platform_post_id="urn:li:share:1111111111111111111"),
        _published_post(platform_post_id="urn:li:share:2222222222222222222"),
        _published_post(platform_post_id="urn:li:share:3333333333333333333"),
    ]

    call_count = 0

    async def fake_fetch_one(client, post, creds, now):
        nonlocal call_count
        call_count += 1
        if post.platform_post_id == "urn:li:share:2222222222222222222":
            raise RuntimeError("Simulated API failure for post 2")
        from app.integrations.linkedin_metrics import _map_snapshot
        return _map_snapshot(post, _SAMPLE_ORG_STATS, now)

    with patch("app.integrations.linkedin_metrics._fetch_one", side_effect=fake_fetch_one):
        # asyncio.sleep must be patched to avoid 5s delays in tests
        with patch("asyncio.sleep", new_callable=AsyncMock):
            snapshots = await fetch(posts, _ORG_CREDS, "linkedin")

    # 2 successes despite 1 failure (fault isolation AD-A10)
    assert len(snapshots) == 2
    assert all(s.unavailable_reason is None for s in snapshots)


# ── 9. Capture wired in dispatch_publish_for_platform ────────────────────────

@pytest.mark.asyncio
async def test_capture_linkedin_post_wired_in_dispatch():
    """dispatch_publish_for_platform calls upsert_published_post for linkedin after publish."""
    # We test that _capture_linkedin_post is invoked by patching upsert_published_post
    # and create_ugc_post, then calling dispatch_publish_for_platform.
    from app.services.publishing import dispatch_publish_for_platform

    campaign_id = uuid.uuid4()
    fake_urn = "urn:li:ugcPost:9999999999999999999"

    mock_campaign = MagicMock()
    mock_campaign.id = campaign_id
    mock_campaign.client_id = uuid.uuid4()
    mock_campaign.linkedin_post = "Test LinkedIn post content"
    mock_campaign.blog_html = "<p>Test</p>"
    mock_campaign.image_url = None   # text-only -> create_ugc_post path

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=MagicMock())

    mock_conn = MagicMock()
    mock_conn.encrypted_credentials = b"encrypted"

    creds_dict = {
        "access_token": "tok_test",
        "target": "organization",
        "org_id": "12345678",
    }

    with patch("app.services.publishing.get_campaign", return_value=mock_campaign), \
         patch("app.services.publishing.get_connection_for_platform", return_value=mock_conn), \
         patch("app.services.publishing.decrypt_credential", return_value=json.dumps(creds_dict)), \
         patch("app.integrations.linkedin.create_ugc_post", new_callable=AsyncMock, return_value=fake_urn) as mock_create, \
         patch("app.services.publishing.upsert_published_post", new_callable=AsyncMock) as mock_upsert:

        result = await dispatch_publish_for_platform(mock_db, campaign_id, "linkedin")

    assert result.get("linkedin") == "success"
    mock_create.assert_awaited_once()
    # upsert_published_post must have been called with platform="linkedin" and the urn
    mock_upsert.assert_awaited_once()
    call_kwargs = mock_upsert.call_args.kwargs
    assert call_kwargs.get("platform") == "linkedin"
    assert call_kwargs.get("platform_post_id") == fake_urn


# ── 10. Read path includes "linkedin" ─────────────────────────────────────────

def test_read_path_includes_linkedin():
    """_METRICS_PLATFORMS in analytics service includes 'linkedin'."""
    from app.services.analytics import _METRICS_PLATFORMS

    assert "linkedin" in _METRICS_PLATFORMS
    # Verify Meta platforms are still present (no regression)
    assert "facebook_page" in _METRICS_PLATFORMS
    assert "instagram" in _METRICS_PLATFORMS
    assert "threads" in _METRICS_PLATFORMS


# ── Additional: _li_unavailable_reason helper ─────────────────────────────────

def test_li_unavailable_reason_401():
    from app.integrations.linkedin_metrics import _li_unavailable_reason
    assert _li_unavailable_reason(401, {}) == "token_expired"


def test_li_unavailable_reason_403():
    from app.integrations.linkedin_metrics import _li_unavailable_reason
    assert _li_unavailable_reason(403, {}) == "scope_missing"


def test_li_unavailable_reason_empty_elements():
    from app.integrations.linkedin_metrics import _li_unavailable_reason
    assert _li_unavailable_reason(200, {"elements": []}) == "no_data_yet"


def test_li_unavailable_reason_unknown():
    from app.integrations.linkedin_metrics import _li_unavailable_reason
    assert _li_unavailable_reason(500, {"error": "server error"}) == "unknown"


# ── Additional: SUPPORTS_METRICS flag ─────────────────────────────────────────

def test_supports_metrics_flag():
    from app.integrations import linkedin_metrics
    assert linkedin_metrics.SUPPORTS_METRICS is True
    assert linkedin_metrics.platform == "linkedin"


# ── 11. LinkedIn-Version header is sent ───────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_one_sends_linkedin_version_header():
    """_fetch_org_stats sends LinkedIn-Version: 202608 and X-Restli-Protocol-Version: 2.0.0."""
    from app.integrations.linkedin_metrics import _fetch_one

    post = _published_post()
    captured_headers: list[dict] = []

    async def fake_get(url, params=None, headers=None, **kwargs):
        captured_headers.append(dict(headers or {}))
        return _httpx_response(200, _SAMPLE_ORG_STATS)

    client = MagicMock()
    client.get = AsyncMock(side_effect=fake_get)

    await _fetch_one(client, post, _ORG_CREDS, _NOW)

    assert captured_headers, "No HTTP request was made"
    h = captured_headers[0]
    assert h.get("LinkedIn-Version") == "202608"
    assert h.get("X-Restli-Protocol-Version") == "2.0.0"


# ── 12. Aggregate fallback snapshot has valid metric data ─────────────────────

@pytest.mark.asyncio
async def test_fetch_one_ugcpost_aggregate_snapshot_has_data():
    """ugcPost URN: org-aggregate stats map to valid metric values (AC #5 verified)."""
    from app.integrations.linkedin_metrics import _fetch_one

    ugc_urn = "urn:li:ugcPost:9876543210987654321"
    post = _published_post(platform_post_id=ugc_urn)

    async def fake_get(url, params=None, headers=None, **kwargs):
        return _httpx_response(200, _SAMPLE_ORG_STATS)

    client = MagicMock()
    client.get = AsyncMock(side_effect=fake_get)

    snap = await _fetch_one(client, post, _ORG_CREDS, _NOW)

    assert snap.unavailable_reason is None
    assert snap.impressions == 1500
    assert snap.engagements == 142   # 45+12+8+77


# ── 13. Fire-and-forget: capture failure does not fail publish ────────────────

@pytest.mark.asyncio
async def test_capture_linkedin_post_failure_does_not_fail_publish():
    """When upsert_published_post raises, dispatch_publish_for_platform still returns success (AD-A10)."""
    from app.services.publishing import dispatch_publish_for_platform

    campaign_id = uuid.uuid4()

    mock_campaign = MagicMock()
    mock_campaign.id = campaign_id
    mock_campaign.client_id = uuid.uuid4()
    mock_campaign.linkedin_post = "Test post"
    mock_campaign.blog_html = "<p>Test</p>"
    mock_campaign.image_url = None

    mock_db = MagicMock()
    mock_conn = MagicMock()
    mock_conn.encrypted_credentials = b"encrypted"

    creds_dict = {
        "access_token": "tok_test",
        "target": "organization",
        "org_id": "12345678",
    }

    with patch("app.services.publishing.get_campaign", return_value=mock_campaign), \
         patch("app.services.publishing.get_connection_for_platform", return_value=mock_conn), \
         patch("app.services.publishing.decrypt_credential", return_value=json.dumps(creds_dict)), \
         patch("app.integrations.linkedin.create_ugc_post", new_callable=AsyncMock, return_value="urn:li:ugcPost:123"), \
         patch("app.services.publishing.upsert_published_post", new_callable=AsyncMock, side_effect=RuntimeError("DB down")):

        result = await dispatch_publish_for_platform(mock_db, campaign_id, "linkedin")

    # Publish must succeed even when capture fails (fire-and-forget, AD-A10)
    assert result.get("linkedin") == "success"


# ── 14. dispatch_publish batch path captures LinkedIn ─────────────────────────

@pytest.mark.asyncio
async def test_dispatch_publish_batch_path_wires_capture():
    """dispatch_publish (batch path) calls upsert_published_post for linkedin after publish (VG #2)."""
    from app.services.publishing import dispatch_publish

    campaign_id = uuid.uuid4()
    job_id = uuid.uuid4()
    fake_urn = "urn:li:ugcPost:8888888888888888888"

    mock_campaign = MagicMock()
    mock_campaign.id = campaign_id
    mock_campaign.client_id = uuid.uuid4()
    mock_campaign.linkedin_post = "Batch path test post"
    mock_campaign.blog_html = "<p>Test</p>"
    mock_campaign.image_url = None
    mock_campaign.status = "approved"  # not "published" → no skip-platform logic

    mock_conn = MagicMock()
    mock_conn.platform = "linkedin"  # plain str so isinstance(str) passes
    mock_conn.encrypted_credentials = b"encrypted"

    creds_dict = {
        "access_token": "tok_test",
        "target": "organization",
        "org_id": "12345678",
    }

    mock_db = MagicMock()

    with patch("app.services.publishing.get_campaign", return_value=mock_campaign), \
         patch("app.services.publishing.get_connections_for_client", new_callable=AsyncMock, return_value=[mock_conn]), \
         patch("app.services.publishing.decrypt_credential", return_value=json.dumps(creds_dict)), \
         patch("app.integrations.linkedin.create_ugc_post", new_callable=AsyncMock, return_value=fake_urn), \
         patch("app.services.publishing.upsert_published_post", new_callable=AsyncMock) as mock_upsert:

        results = await dispatch_publish(mock_db, campaign_id, job_id)

    assert results.get("linkedin") == "success"
    mock_upsert.assert_awaited_once()
    call_kwargs = mock_upsert.call_args.kwargs
    assert call_kwargs.get("platform") == "linkedin"
    assert call_kwargs.get("platform_post_id") == fake_urn


# ── 15. Image path (share URN) capture ───────────────────────────────────────

@pytest.mark.asyncio
async def test_dispatch_publish_for_platform_image_path_captures_share_urn():
    """Image path (create_post_with_image) returns a share URN, which is persisted (AC #2)."""
    from app.services.publishing import dispatch_publish_for_platform

    campaign_id = uuid.uuid4()
    share_urn = "urn:li:share:7777777777777777777"

    mock_campaign = MagicMock()
    mock_campaign.id = campaign_id
    mock_campaign.client_id = uuid.uuid4()
    mock_campaign.linkedin_post = "Post with image"
    mock_campaign.blog_html = "<p>Test</p>"
    mock_campaign.image_url = "https://example.com/img.jpg"

    mock_db = MagicMock()
    mock_conn = MagicMock()
    mock_conn.encrypted_credentials = b"encrypted"

    creds_dict = {
        "access_token": "tok_org",
        "target": "organization",
        "org_id": "12345678",
    }

    # Mock the httpx.AsyncClient used to download the image
    mock_img_resp = MagicMock()
    mock_img_resp.content = b"fake_image_bytes"
    mock_img_resp.raise_for_status = MagicMock()
    mock_img_client = AsyncMock()
    mock_img_client.get = AsyncMock(return_value=mock_img_resp)
    mock_ctx_mgr = MagicMock()
    mock_ctx_mgr.__aenter__ = AsyncMock(return_value=mock_img_client)
    mock_ctx_mgr.__aexit__ = AsyncMock(return_value=None)

    with patch("app.services.publishing.get_campaign", return_value=mock_campaign), \
         patch("app.services.publishing.get_connection_for_platform", return_value=mock_conn), \
         patch("app.services.publishing.decrypt_credential", return_value=json.dumps(creds_dict)), \
         patch("app.services.publishing.httpx.AsyncClient", return_value=mock_ctx_mgr), \
         patch("app.integrations.linkedin.upload_image", new_callable=AsyncMock, return_value="urn:li:image:123"), \
         patch("app.integrations.linkedin.create_post_with_image", new_callable=AsyncMock, return_value=share_urn) as mock_create_img, \
         patch("app.services.publishing.upsert_published_post", new_callable=AsyncMock) as mock_upsert:

        result = await dispatch_publish_for_platform(mock_db, campaign_id, "linkedin")

    assert result.get("linkedin") == "success"
    mock_create_img.assert_awaited_once()
    mock_upsert.assert_awaited_once()
    call_kwargs = mock_upsert.call_args.kwargs
    assert call_kwargs.get("platform") == "linkedin"
    assert call_kwargs.get("platform_post_id") == share_urn
    assert share_urn.startswith("urn:li:share:"), "persisted URN must be a share URN"


# ── 16. Schema Literal accepts "linkedin" ─────────────────────────────────────

def test_schema_platform_literal_accepts_linkedin():
    """BestPost and PostMetricItem schemas accept platform='linkedin' (AC #8)."""
    from app.schemas.analytics import BestPost, PostMetricItem

    best = BestPost(
        published_post_id=uuid.uuid4(),
        platform="linkedin",
        campaign_title="LinkedIn Test",
        engagements=142,
        permalink="https://www.linkedin.com/feed/update/urn:li:share:123",
    )
    assert best.platform == "linkedin"

    item = PostMetricItem(
        published_post_id=uuid.uuid4(),
        platform="linkedin",
        campaign_title="LinkedIn Test",
        campaign_excerpt=None,
        latest_impressions=1500,
        latest_engagements=142,
        latest_likes=45,
        latest_comments=12,
        latest_shares=8,
        engagement_rate=0.0947,
        permalink=None,
        captured_at=_NOW,
        series=[],
        unavailable_reason=None,
    )
    assert item.platform == "linkedin"


# ── 17. Worker _METRICS_PLATFORMS includes linkedin ───────────────────────────

def test_worker_metrics_platforms_includes_linkedin():
    """_METRICS_PLATFORMS in workers/analytics.py includes 'linkedin' (AC #6)."""
    from app.workers.analytics import _METRICS_PLATFORMS

    assert "linkedin" in _METRICS_PLATFORMS
    assert "facebook_page" in _METRICS_PLATFORMS
    assert "instagram" in _METRICS_PLATFORMS
    assert "threads" in _METRICS_PLATFORMS


# ══════════════════════════════════════════════════════════════════════════════
# Story 25.2 — LinkedIn personal-profile (member) analytics
# ══════════════════════════════════════════════════════════════════════════════

_MEMBER_CREDS = {
    "access_token": "tok_member",
    "org_id": None,
    "target": "personal",
    "scopes": "openid profile w_member_social r_member_postAnalytics",
}

_MEMBER_CREDS_NO_SCOPE = {
    "access_token": "tok_member",
    "org_id": None,
    "target": "personal",
    "scopes": "openid profile w_member_social",  # predates the analytics scope grant
}

# A representative memberCreatorPostAnalytics per-metric total (li-lms-2026-08 flat form).
def _member_metric_response(metric: str, count: int) -> httpx.Response:
    body = {
        "elements": [
            {
                "count": count,
                "metricType": metric,
                "targetEntity": {"share": "urn:li:share:7214567890123456789"},
            }
        ],
        "paging": {"count": 10, "start": 0, "links": []},
    }
    return _httpx_response(200, body)


def _member_counts_fake(counts: dict):
    """Build a fake client.get that returns per-metric totals from a {metric: count} dict.

    Metrics not present in the dict return an empty elements list (no data)."""
    captured_urls: list[str] = []

    async def fake_get(url, params=None, headers=None, **kwargs):
        captured_urls.append(url)
        # queryType={METRIC} is the last recognizable segment of the URL
        metric = None
        for part in url.split("&"):
            if part.startswith("queryType="):
                metric = part.split("=", 1)[1]
                break
        if metric in counts:
            return _member_metric_response(metric, counts[metric])
        return _httpx_response(200, {"elements": []})

    return fake_get, captured_urls


# ── Member 1. entity param encoding ───────────────────────────────────────────

def test_member_entity_param_share_and_ugc():
    from app.integrations.linkedin_metrics import _member_entity_param

    assert _member_entity_param("urn:li:share:123") == "(share:urn%3Ali%3Ashare%3A123)"
    assert _member_entity_param("urn:li:ugcPost:456") == "(ugc:urn%3Ali%3AugcPost%3A456)"
    assert _member_entity_param("urn:li:activity:789") is None
    assert _member_entity_param("") is None


# ── Member 2. snapshot mapping ────────────────────────────────────────────────

def test_map_member_snapshot_full():
    """Collected member counts map to normalized columns (AC #4)."""
    from app.integrations.linkedin_metrics import _map_member_snapshot

    counts = {
        "IMPRESSION": 2000,
        "MEMBERS_REACHED": 1800,
        "REACTION": 50,
        "COMMENT": 10,
        "RESHARE": 5,
        "POST_SAVE": 3,
        "LINK_CLICKS": 20,
        "POST_SEND": 7,
        "FOLLOWER_GAINED_FROM_CONTENT": 2,
        "PROFILE_VIEW_FROM_CONTENT": 15,
    }
    post = _published_post(target="personal")
    snap = _map_member_snapshot(post, counts, _NOW)

    assert snap.impressions == 2000               # IMPRESSION preferred
    assert snap.likes == 50                        # REACTION
    assert snap.comments == 10                     # COMMENT
    assert snap.shares == 5                         # RESHARE
    # engagements = REACTION + COMMENT + RESHARE + POST_SAVE + LINK_CLICKS
    assert snap.engagements == 50 + 10 + 5 + 3 + 20
    assert snap.unavailable_reason is None
    assert snap.platform == "linkedin"
    # All raw counts preserved
    assert snap.raw["memberCreatorPostAnalytics"]["POST_SEND"] == 7
    assert snap.raw["memberCreatorPostAnalytics"]["PROFILE_VIEW_FROM_CONTENT"] == 15


def test_map_member_snapshot_impression_fallback_to_members_reached():
    """IMPRESSION absent -> impressions falls back to MEMBERS_REACHED."""
    from app.integrations.linkedin_metrics import _map_member_snapshot

    counts = {"MEMBERS_REACHED": 1800, "REACTION": 4}
    post = _published_post(target="personal")
    snap = _map_member_snapshot(post, counts, _NOW)
    assert snap.impressions == 1800
    assert snap.engagements == 4


def test_map_member_snapshot_no_engagement_yields_none():
    """No engagement metrics -> engagements None, not fabricated zero (AD-A5)."""
    from app.integrations.linkedin_metrics import _map_member_snapshot

    counts = {"IMPRESSION": 100}
    post = _published_post(target="personal")
    snap = _map_member_snapshot(post, counts, _NOW)
    assert snap.impressions == 100
    assert snap.engagements is None
    assert snap.likes is None


# ── Member 3. flag gating ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_member_scope_missing_no_api_call():
    """Flag on but connection lacks r_member_postAnalytics -> member_scope_missing, no API call."""
    from app.integrations.linkedin_metrics import _fetch_one

    post = _published_post(platform_post_id="urn:li:ugcPost:123", target="personal")
    client = MagicMock()
    client.get = AsyncMock()

    with patch("app.integrations.linkedin_metrics.settings.LINKEDIN_MEMBER_METRICS_ENABLED", True):
        snap = await _fetch_one(client, post, _MEMBER_CREDS_NO_SCOPE, _NOW)

    assert snap.unavailable_reason == "member_scope_missing"
    client.get.assert_not_called()


# ── Member 4. happy path: flag on + scope present ─────────────────────────────

@pytest.mark.asyncio
async def test_member_fetch_maps_metrics_share_urn():
    """Flag on + scope + share URN -> memberCreatorPostAnalytics per metric -> mapped snapshot."""
    from app.integrations.linkedin_metrics import _fetch_one

    post = _published_post(platform_post_id="urn:li:share:7214567890123456789", target="personal")
    counts = {"IMPRESSION": 900, "REACTION": 12, "COMMENT": 3, "RESHARE": 1, "LINK_CLICKS": 4}
    fake_get, captured_urls = _member_counts_fake(counts)
    client = MagicMock()
    client.get = AsyncMock(side_effect=fake_get)

    with patch("app.integrations.linkedin_metrics.settings.LINKEDIN_MEMBER_METRICS_ENABLED", True):
        snap = await _fetch_one(client, post, _MEMBER_CREDS, _NOW)

    assert snap.unavailable_reason is None
    assert snap.impressions == 900
    assert snap.engagements == 12 + 3 + 1 + 4
    assert snap.likes == 12
    # calls hit the member endpoint with share entity encoding
    assert all("memberCreatorPostAnalytics" in u for u in captured_urls)
    assert any("entity=(share:urn%3Ali%3Ashare%3A7214567890123456789)" in u for u in captured_urls)
    assert any("queryType=IMPRESSION" in u for u in captured_urls)


@pytest.mark.asyncio
async def test_member_fetch_ugcpost_uses_ugc_entity():
    """ugcPost URN -> entity uses (ugc:...) encoding."""
    from app.integrations.linkedin_metrics import _fetch_one

    post = _published_post(platform_post_id="urn:li:ugcPost:9876543210987654321", target="personal")
    fake_get, captured_urls = _member_counts_fake({"IMPRESSION": 10})
    client = MagicMock()
    client.get = AsyncMock(side_effect=fake_get)

    with patch("app.integrations.linkedin_metrics.settings.LINKEDIN_MEMBER_METRICS_ENABLED", True):
        snap = await _fetch_one(client, post, _MEMBER_CREDS, _NOW)

    assert snap.unavailable_reason is None
    assert any("entity=(ugc:urn%3Ali%3AugcPost%3A9876543210987654321)" in u for u in captured_urls)


@pytest.mark.asyncio
async def test_member_fetch_all_empty_returns_no_data_yet():
    """Flag on + scope + share URN but every metric returns no data -> no_data_yet."""
    from app.integrations.linkedin_metrics import _fetch_one

    post = _published_post(platform_post_id="urn:li:share:1", target="personal")
    fake_get, _ = _member_counts_fake({})  # nothing -> all empty
    client = MagicMock()
    client.get = AsyncMock(side_effect=fake_get)

    with patch("app.integrations.linkedin_metrics.settings.LINKEDIN_MEMBER_METRICS_ENABLED", True):
        snap = await _fetch_one(client, post, _MEMBER_CREDS, _NOW)

    assert snap.unavailable_reason == "no_data_yet"


# ── Member 5. auth/consent errors ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_member_fetch_401_token_expired():
    from app.integrations.linkedin_metrics import _fetch_one

    post = _published_post(platform_post_id="urn:li:share:1", target="personal")

    async def fake_get(url, params=None, headers=None, **kwargs):
        return _httpx_response(401, {"message": "Unauthorized"})

    client = MagicMock()
    client.get = AsyncMock(side_effect=fake_get)

    with patch("app.integrations.linkedin_metrics.settings.LINKEDIN_MEMBER_METRICS_ENABLED", True):
        snap = await _fetch_one(client, post, _MEMBER_CREDS, _NOW)

    assert snap.unavailable_reason == "token_expired"


@pytest.mark.asyncio
async def test_member_fetch_403_consent_revoked():
    """403 without a scope/permission hint -> consent_revoked (scope was pre-flight verified)."""
    from app.integrations.linkedin_metrics import _fetch_one

    post = _published_post(platform_post_id="urn:li:share:1", target="personal")

    async def fake_get(url, params=None, headers=None, **kwargs):
        return _httpx_response(403, {"message": "Access denied for this member"})

    client = MagicMock()
    client.get = AsyncMock(side_effect=fake_get)

    with patch("app.integrations.linkedin_metrics.settings.LINKEDIN_MEMBER_METRICS_ENABLED", True):
        snap = await _fetch_one(client, post, _MEMBER_CREDS, _NOW)

    assert snap.unavailable_reason == "consent_revoked"


@pytest.mark.asyncio
async def test_member_fetch_403_scope_hint_member_scope_missing():
    """403 whose body names a scope/permission gap -> member_scope_missing (not the org scope_missing)."""
    from app.integrations.linkedin_metrics import _fetch_one

    post = _published_post(platform_post_id="urn:li:share:1", target="personal")

    async def fake_get(url, params=None, headers=None, **kwargs):
        return _httpx_response(403, {"message": "Not enough permissions - missing scope"})

    client = MagicMock()
    client.get = AsyncMock(side_effect=fake_get)

    with patch("app.integrations.linkedin_metrics.settings.LINKEDIN_MEMBER_METRICS_ENABLED", True):
        snap = await _fetch_one(client, post, _MEMBER_CREDS, _NOW)

    assert snap.unavailable_reason == "member_scope_missing"


@pytest.mark.asyncio
async def test_member_fetch_single_metric_400_is_skipped():
    """A 400 on one metric is skipped (AD-A10); remaining metrics still produce a snapshot."""
    from app.integrations.linkedin_metrics import _fetch_one

    post = _published_post(platform_post_id="urn:li:share:1", target="personal")

    async def fake_get(url, params=None, headers=None, **kwargs):
        if "queryType=POST_SEND" in url:
            return _httpx_response(400, {"message": "unsupported"})
        if "queryType=IMPRESSION" in url:
            return _member_metric_response("IMPRESSION", 500)
        if "queryType=REACTION" in url:
            return _member_metric_response("REACTION", 8)
        return _httpx_response(200, {"elements": []})

    client = MagicMock()
    client.get = AsyncMock(side_effect=fake_get)

    with patch("app.integrations.linkedin_metrics.settings.LINKEDIN_MEMBER_METRICS_ENABLED", True):
        snap = await _fetch_one(client, post, _MEMBER_CREDS, _NOW)

    assert snap.unavailable_reason is None
    assert snap.impressions == 500
    assert snap.engagements == 8


# ── Member 6. reason mapper unit ──────────────────────────────────────────────

def test_member_unavailable_reason_mapping():
    from app.integrations.linkedin_metrics import _member_unavailable_reason

    assert _member_unavailable_reason(401, {}) == "token_expired"
    assert _member_unavailable_reason(403, {"message": "denied"}) == "consent_revoked"
    assert _member_unavailable_reason(403, {"message": "missing scope"}) == "member_scope_missing"
    assert _member_unavailable_reason(200, {"elements": []}) == "unknown"
    assert _member_unavailable_reason(500, {}) == "unknown"


# ── Member 7. harvester target-branch routing (org vs member) ─────────────────

@pytest.mark.asyncio
async def test_target_branch_org_vs_member_routing():
    """org creds -> org stats endpoint; personal creds -> member endpoint (AC #6)."""
    from app.integrations.linkedin_metrics import _fetch_one

    # Org branch
    org_post = _published_post(platform_post_id="urn:li:share:111", target="organization")
    org_urls: list[str] = []

    async def org_get(url, params=None, headers=None, **kwargs):
        org_urls.append(url)
        return _httpx_response(200, _SAMPLE_ORG_STATS)

    org_client = MagicMock()
    org_client.get = AsyncMock(side_effect=org_get)
    org_snap = await _fetch_one(org_client, org_post, _ORG_CREDS, _NOW)
    assert org_snap.unavailable_reason is None
    assert all("organizationalEntityShareStatistics" in u for u in org_urls)
    assert all("memberCreatorPostAnalytics" not in u for u in org_urls)

    # Member branch
    member_post = _published_post(platform_post_id="urn:li:share:222", target="personal")
    fake_get, member_urls = _member_counts_fake({"IMPRESSION": 5})
    member_client = MagicMock()
    member_client.get = AsyncMock(side_effect=fake_get)
    with patch("app.integrations.linkedin_metrics.settings.LINKEDIN_MEMBER_METRICS_ENABLED", True):
        member_snap = await _fetch_one(member_client, member_post, _MEMBER_CREDS, _NOW)
    assert member_snap.unavailable_reason is None
    assert all("memberCreatorPostAnalytics" in u for u in member_urls)
    assert all("organizationalEntityShareStatistics" not in u for u in member_urls)


# ── Member 8. version header on member calls ──────────────────────────────────

@pytest.mark.asyncio
async def test_member_fetch_sends_linkedin_version_header():
    from app.integrations.linkedin_metrics import _fetch_one

    post = _published_post(platform_post_id="urn:li:share:1", target="personal")
    captured_headers: list[dict] = []

    async def fake_get(url, params=None, headers=None, **kwargs):
        captured_headers.append(dict(headers or {}))
        if "queryType=IMPRESSION" in url:
            return _member_metric_response("IMPRESSION", 1)
        return _httpx_response(200, {"elements": []})

    client = MagicMock()
    client.get = AsyncMock(side_effect=fake_get)

    with patch("app.integrations.linkedin_metrics.settings.LINKEDIN_MEMBER_METRICS_ENABLED", True):
        await _fetch_one(client, post, _MEMBER_CREDS, _NOW)

    assert captured_headers
    assert captured_headers[0].get("LinkedIn-Version") == "202608"
    assert captured_headers[0].get("X-Restli-Protocol-Version") == "2.0.0"


# ── Member 9. personal-post capture (AC #5) ───────────────────────────────────

@pytest.mark.asyncio
async def test_capture_personal_linkedin_post_persisted():
    """A personal (target=personal) LinkedIn publish still persists a published_posts row (AC #5)."""
    from app.services.publishing import dispatch_publish_for_platform

    campaign_id = uuid.uuid4()
    fake_urn = "urn:li:ugcPost:5555555555555555555"

    mock_campaign = MagicMock()
    mock_campaign.id = campaign_id
    mock_campaign.client_id = uuid.uuid4()
    mock_campaign.linkedin_post = "Personal profile post"
    mock_campaign.blog_html = "<p>Test</p>"
    mock_campaign.image_url = None  # text-only -> create_ugc_post path

    mock_db = MagicMock()
    mock_conn = MagicMock()
    mock_conn.encrypted_credentials = b"encrypted"

    creds_dict = {"access_token": "tok_member", "target": "personal", "org_id": None}

    with patch("app.services.publishing.get_campaign", return_value=mock_campaign), \
         patch("app.services.publishing.get_connection_for_platform", return_value=mock_conn), \
         patch("app.services.publishing.decrypt_credential", return_value=json.dumps(creds_dict)), \
         patch("app.integrations.linkedin.create_ugc_post", new_callable=AsyncMock, return_value=fake_urn), \
         patch("app.services.publishing.upsert_published_post", new_callable=AsyncMock) as mock_upsert:

        result = await dispatch_publish_for_platform(mock_db, campaign_id, "linkedin")

    assert result.get("linkedin") == "success"
    mock_upsert.assert_awaited_once()
    call_kwargs = mock_upsert.call_args.kwargs
    assert call_kwargs.get("platform") == "linkedin"
    assert call_kwargs.get("platform_post_id") == fake_urn


# ── Member 10. capability detection in connections list (AC #1) ───────────────

def test_extract_linkedin_target_member_capable():
    """_extract_linkedin_target derives member_capable from r_member_postAnalytics scope."""
    from unittest.mock import patch as _patch
    from app.routers.publishing import _extract_linkedin_target

    with _patch(
        "app.routers.publishing.decrypt_credential",
        return_value=json.dumps({"target": "personal", "scopes": "openid r_member_postAnalytics"}),
    ):
        target, org_name, org_capable, member_capable = _extract_linkedin_target(b"x")
    assert member_capable is True
    assert target == "personal"

    with _patch(
        "app.routers.publishing.decrypt_credential",
        return_value=json.dumps({"target": "personal", "scopes": "openid w_member_social"}),
    ):
        _, _, _, member_capable2 = _extract_linkedin_target(b"x")
    assert member_capable2 is False
