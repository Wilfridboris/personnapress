"""Meta Graph API insights integration for Facebook Page, Instagram, and Threads posts.

Normalized metric mapping (AD-A3 convention):
  impressions  <- FB: post_impressions | IG: views (fallback reach) | Threads: views
  engagements  <- FB: reactions+comments+shares | IG: likes+comments+saved+shares | Threads: likes+replies+reposts+quotes

FB Page insights require 100+ page likes; below that threshold the API returns an
  error and we record unavailable_reason="page_under_100_likes" (no fabricated zeros).

Instagram `impressions` was removed in Graph v21 (Jan 2025); `views` is the replacement.

Threads endpoint/metric names: VERIFY against live Threads API at deploy time.
  The endpoint and field names below are correct as of Aug 2026 but Meta evolves them.

Facebook Page Insights metric set post-June-2026-deprecation:
  VERIFY: run GET /{post_id}/insights?metric=<FB_METRICS> with a real post to confirm
  the metrics below are still available after the June 2026 Insights API update.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import httpx
import sentry_sdk

logger = logging.getLogger(__name__)

SUPPORTS_METRICS = True
META_PLATFORMS = frozenset({"facebook_page", "instagram", "threads"})

META_GRAPH_VERSION = "v21.0"
_GRAPH_BASE = f"https://graph.facebook.com/{META_GRAPH_VERSION}"

# Facebook Page post metric set (post-June-2026-deprecation; verify at deploy)
_FB_METRICS = "post_impressions,post_engaged_users,post_reactions_by_type_total"

# Instagram media metric set (impressions removed in v21; views is the replacement)
_IG_METRICS = "views,reach,likes,comments,saved,shares"

# Threads media metric set (verify field names against live API at deploy time)
_THREADS_METRICS = "views,likes,replies,reposts,quotes"

# Unavailability reason codes (machine-readable; consumed by Story 24-3)
_REASON_PAGE_UNDER_100_LIKES = "page_under_100_likes"
_REASON_PERMISSION_MISSING = "permission_missing"
_REASON_NO_DATA_YET = "no_data_yet"
_REASON_UNKNOWN = "unknown"


@dataclass
class MetricSnapshot:
    """Normalized engagement snapshot for one post at one point in time.

    When `unavailable_reason` is set the row is an unavailability record —
    impressions/engagements are None, raw carries the API error payload.
    Only ever INSERTed; never updated (AD-A3).
    """
    published_post_id: uuid.UUID
    client_id: uuid.UUID
    platform: str
    captured_at: datetime
    impressions: Optional[int] = None
    engagements: Optional[int] = None
    raw: dict = field(default_factory=dict)
    unavailable_reason: Optional[str] = None


async def fetch(
    posts: list,  # list[PublishedPost]
    creds: dict,
    platform: str,
) -> list[MetricSnapshot]:
    """Fetch insights for a batch of published posts from a single Meta platform.

    Fault-isolated per item (AD-A10): one post failing is caught, logged to Sentry,
    and skipped. The sweep continues for all other posts.
    Credentials never logged (decrypted creds stay in local scope only).
    """
    results: list[MetricSnapshot] = []
    now = datetime.now(timezone.utc)

    async with httpx.AsyncClient(timeout=15.0) as client:
        for i, post in enumerate(posts):
            if i > 0:
                # Stagger between individual post fetches to avoid bursting Meta's rate limits.
                await asyncio.sleep(0.2)
            try:
                snapshot = await _fetch_one(client, post, creds, platform, now)
                results.append(snapshot)
            except Exception as exc:
                logger.error(
                    "meta_metrics fetch error platform=%s post_id=%s: %s",
                    platform,
                    getattr(post, "platform_post_id", "?"),
                    exc,
                    exc_info=True,
                )
                sentry_sdk.capture_exception(exc)
    return results


async def _fetch_one(
    client: httpx.AsyncClient,
    post,
    creds: dict,
    platform: str,
    now: datetime,
) -> MetricSnapshot:
    if platform == "facebook_page":
        return await _fetch_facebook(client, post, creds, now)
    if platform == "instagram":
        return await _fetch_instagram(client, post, creds, now)
    if platform == "threads":
        return await _fetch_threads(client, post, creds, now)
    raise ValueError(f"meta_metrics: unsupported platform '{platform}'")


# ── Facebook Page ─────────────────────────────────────────────────────────────

async def _fetch_facebook(client, post, creds: dict, now: datetime) -> MetricSnapshot:
    token = creds["page_access_token"]
    resp = await client.get(
        f"{_GRAPH_BASE}/{post.platform_post_id}/insights",
        params={"metric": _FB_METRICS, "access_token": token},
    )
    raw = _safe_json(resp)

    if resp.status_code != 200:
        reason = _fb_unavailable_reason(raw.get("error", {}))
        if reason:
            logger.info(
                "meta_metrics FB unavailable post=%s reason=%s",
                post.platform_post_id,
                reason,
            )
            return MetricSnapshot(
                published_post_id=post.id,
                client_id=post.client_id,
                platform="facebook_page",
                captured_at=now,
                raw=raw,
                unavailable_reason=reason,
            )
        resp.raise_for_status()

    return _map_facebook_snapshot(post, raw, now)


def _fb_unavailable_reason(error: dict) -> Optional[str]:
    """Map a Meta API error dict to a machine-readable unavailability reason.

    Returns None if the error is transient (should be raised, not recorded as unavailable).
    """
    code = error.get("code")
    subcode = error.get("error_subcode")

    # Page with fewer than 100 likes has no insights
    if code == 100 and subcode == 33:
        return _REASON_PAGE_UNDER_100_LIKES
    # Permission not granted (read_insights missing)
    if code == 10 or code == 200:
        return _REASON_PERMISSION_MISSING
    # Post too new / no data collected yet
    if code == 100 and subcode == 2108006:
        return _REASON_NO_DATA_YET
    # Token expired / unauthorized — this is transient; re-raise so worker retries next cadence
    if code == 190:
        return None
    # Unknown unavailability or non-standard error body — record rather than raise so sweep continues
    return _REASON_UNKNOWN


def _map_facebook_snapshot(post, raw: dict, now: datetime) -> MetricSnapshot:
    """Map a FB insights API response to normalized columns.

    raw["data"] is a list of {name, values} dicts. Each metric has a list of
    values with {value, end_time}; we take the first (most recent period).
    """
    metrics_by_name: dict[str, int] = {}
    for item in raw.get("data", []):
        name = item.get("name", "")
        values = item.get("values", [{}])
        val = values[0].get("value", 0) if values else 0
        if isinstance(val, dict):
            # post_reactions_by_type_total returns {LIKE: n, LOVE: n, ...}
            val = sum(v for v in val.values() if isinstance(v, int))
        metrics_by_name[name] = int(val) if val else 0

    impressions = metrics_by_name.get("post_impressions")
    # Prefer post_engaged_users (broader signal) over reactions; use explicit key presence
    # check so a legitimate zero doesn't fall through to the reactions fallback.
    if "post_engaged_users" in metrics_by_name:
        engagements = metrics_by_name["post_engaged_users"]
    else:
        engagements = metrics_by_name.get("post_reactions_by_type_total")

    return MetricSnapshot(
        published_post_id=post.id,
        client_id=post.client_id,
        platform="facebook_page",
        captured_at=now,
        impressions=impressions,
        engagements=engagements,
        raw=raw,
    )


# ── Instagram ─────────────────────────────────────────────────────────────────

async def _fetch_instagram(client, post, creds: dict, now: datetime) -> MetricSnapshot:
    token = creds["page_access_token"]
    resp = await client.get(
        f"{_GRAPH_BASE}/{post.platform_post_id}/insights",
        params={"metric": _IG_METRICS, "access_token": token},
    )
    raw = _safe_json(resp)

    if resp.status_code != 200:
        reason = _ig_unavailable_reason(raw.get("error", {}))
        if reason:
            logger.info(
                "meta_metrics IG unavailable post=%s reason=%s",
                post.platform_post_id,
                reason,
            )
            return MetricSnapshot(
                published_post_id=post.id,
                client_id=post.client_id,
                platform="instagram",
                captured_at=now,
                raw=raw,
                unavailable_reason=reason,
            )
        resp.raise_for_status()

    return _map_instagram_snapshot(post, raw, now)


def _ig_unavailable_reason(error: dict) -> Optional[str]:
    code = error.get("code")
    if code == 10 or code == 200:
        return _REASON_PERMISSION_MISSING
    if code == 100:
        return _REASON_NO_DATA_YET
    if code == 190:
        return None  # transient; re-raise
    return _REASON_UNKNOWN


def _map_instagram_snapshot(post, raw: dict, now: datetime) -> MetricSnapshot:
    """Map an IG insights API response to normalized columns.

    impressions <- views (IG v21+ replacement for the removed `impressions` metric)
                   fallback to reach if views absent.
    engagements <- likes + comments + saved + shares
    """
    m = _ig_metrics_dict(raw)

    impressions = m.get("views") or m.get("reach")
    engagements = (
        (m.get("likes") or 0)
        + (m.get("comments") or 0)
        + (m.get("saved") or 0)
        + (m.get("shares") or 0)
    ) or None

    return MetricSnapshot(
        published_post_id=post.id,
        client_id=post.client_id,
        platform="instagram",
        captured_at=now,
        impressions=impressions,
        engagements=engagements,
        raw=raw,
    )


def _ig_metrics_dict(raw: dict) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in raw.get("data", []):
        name = item.get("name", "")
        # IG insights values list has one entry per period; take the first
        values = item.get("values", [{}])
        val = values[0].get("value", 0) if values else 0
        result[name] = int(val) if val else 0
    return result


# ── Threads ───────────────────────────────────────────────────────────────────

async def _fetch_threads(client, post, creds: dict, now: datetime) -> MetricSnapshot:
    # Threads uses user_access_token (not page_access_token)
    token = creds["user_access_token"]
    resp = await client.get(
        f"{_GRAPH_BASE}/{post.platform_post_id}/insights",
        params={"metric": _THREADS_METRICS, "access_token": token},
    )
    raw = _safe_json(resp)

    if resp.status_code != 200:
        reason = _threads_unavailable_reason(raw.get("error", {}))
        if reason:
            logger.info(
                "meta_metrics Threads unavailable post=%s reason=%s",
                post.platform_post_id,
                reason,
            )
            return MetricSnapshot(
                published_post_id=post.id,
                client_id=post.client_id,
                platform="threads",
                captured_at=now,
                raw=raw,
                unavailable_reason=reason,
            )
        resp.raise_for_status()

    return _map_threads_snapshot(post, raw, now)


def _threads_unavailable_reason(error: dict) -> Optional[str]:
    code = error.get("code")
    if code == 10 or code == 200:
        return _REASON_PERMISSION_MISSING
    if code == 100:
        return _REASON_NO_DATA_YET
    if code == 190:
        return None  # transient; re-raise
    return _REASON_UNKNOWN


def _map_threads_snapshot(post, raw: dict, now: datetime) -> MetricSnapshot:
    """Map a Threads insights API response to normalized columns.

    impressions <- views
    engagements <- likes + replies + reposts + quotes
    Field names verified against Threads API Aug 2026; re-verify on Meta changelog updates.
    """
    m = _threads_metrics_dict(raw)

    impressions = m.get("views")
    engagements = (
        (m.get("likes") or 0)
        + (m.get("replies") or 0)
        + (m.get("reposts") or 0)
        + (m.get("quotes") or 0)
    ) or None

    return MetricSnapshot(
        published_post_id=post.id,
        client_id=post.client_id,
        platform="threads",
        captured_at=now,
        impressions=impressions,
        engagements=engagements,
        raw=raw,
    )


def _threads_metrics_dict(raw: dict) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in raw.get("data", []):
        name = item.get("name", "")
        val = item.get("value", 0)
        result[name] = int(val) if val else 0
    return result


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_json(resp: httpx.Response) -> dict:
    try:
        return resp.json()
    except Exception:
        return {"_raw_text": resp.text[:500]}
