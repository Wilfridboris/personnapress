"""Meta Graph API insights integration for Facebook Page, Instagram, and Threads posts.

Normalized metric mapping (AD-A3 convention):
  impressions  <- FB: post_media_view (probe candidate, likely NULL — see Story 24.5 Dev Notes)
                     | IG: views (fallback reach) | Threads: views
  engagements  <- FB: sum(post_reactions_*_total)+comments+shares (NULL-safe) | IG: likes+comments+saved+shares | Threads: likes+replies+reposts+quotes
  likes        <- FB: sum of post_reactions_*_total individual counters | IG: likes | Threads: likes
  comments     <- FB: comments.summary(true).total_count (object-edge) | IG: comments | Threads: replies
  shares       <- FB: shares.count (object-edge) | IG: shares | Threads: reposts

Story 24.4 amendment (AD-A7): the normalized set now includes a bounded set of
  engagement-component columns (likes, comments, shares) alongside engagements.
  AD-A7 previously allowed only (impressions, engagements). engagements formula is
  unchanged; saves (IG) is NOT promoted — it stays inside engagements + raw.

Story 24.5 (Meta API drift fix):
  - FB: removed deprecated post_impressions/post_engaged_users/post_reactions_by_type_total.
    Reactions mapped via individual post_reactions_*_total counters (June 2026 deprecation).
    post_media_view included as a probe for impressions — expected NULL per Meta docs.
    impressions = NULL is the primary outcome; engagements = reactions+comments+shares.
  - Threads: fixed host from graph.facebook.com -> graph.threads.com (THREADS_GRAPH_BASE).
    Fixed _threads_metrics_dict to read values[0].value (list form, matching FB/IG).
  - Constants: both FB/IG base and Threads base now derived from meta.py (single source of truth).

FB Page insights require 100+ page likes; below that threshold the API returns an
  error and we record unavailable_reason="page_under_100_likes" (no fabricated zeros).

Instagram `impressions` was removed in Graph v21 (Jan 2025); `views` is the replacement.
Instagram continues to work at v25 — no metric set changes needed (Story 24.5 AC #7).

Threads endpoint/metric names: VERIFY against live Threads API at deploy time.
  Requires threads_manage_insights permission.
  The endpoint and field names below are correct as of Aug 2026 but Meta evolves them.

Facebook Page Insights metric set post-June-2026-deprecation:
  post_impressions, post_engaged_users, post_reactions_by_type_total are all INVALID
  as of June 15 2026 (Meta Page Insights deprecation). The valid per-post metrics are
  the individual post_reactions_*_total counters plus the speculative post_media_view.
  If no views metric returns 200, impressions is NULL (primary expected outcome, not fallback).
  Do NOT use post_impressions or page_impressions_unique (page-level reach, not per-post).

Facebook comments/shares are NOT available from the insights endpoint:
  They come from a second object-edge call GET /{post_id}?fields=comments.summary(true),shares
  (AC #4). This second call is fault-isolated — failure degrades comments/shares to NULL
  without losing the primary impressions/engagements snapshot (AD-A10).
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import httpx
import sentry_sdk

from app.integrations.meta import META_GRAPH_BASE, THREADS_GRAPH_BASE

logger = logging.getLogger(__name__)

SUPPORTS_METRICS = True
META_PLATFORMS = frozenset({"facebook_page", "instagram", "threads"})

# Facebook Page post metric set (post-June-2026-deprecation).
# post_impressions, post_engaged_users, and post_reactions_by_type_total are all
# invalid after Meta's June 15 2026 Page Insights deprecation — the API rejects the
# entire call if any deprecated metric is present (#100 "not a valid insights metric").
# post_media_view is a speculative probe for per-post views; expected to return NULL
# on standard-tier tokens (Meta docs show no confirmed per-post impressions metric).
# Reactions via individual per-type counters are the only confirmed valid per-post metrics.
_FB_METRICS = (
    "post_reactions_like_total,"
    "post_reactions_love_total,"
    "post_reactions_wow_total,"
    "post_reactions_haha_total,"
    "post_reactions_sorry_total,"
    "post_reactions_anger_total,"
    "post_media_view"
)

# Instagram media metric set (impressions removed in v21; views is the replacement)
_IG_METRICS = "views,reach,likes,comments,saved,shares"

# Threads media metric set (verify field names against live API at deploy time)
_THREADS_METRICS = "views,likes,replies,reposts,quotes"

# Per-type Facebook reaction counters (replaces deprecated post_reactions_by_type_total).
# If Meta adds a new reaction type (e.g. post_reactions_care_total), add it here.
_FB_REACTION_METRICS = frozenset({
    "post_reactions_like_total",
    "post_reactions_love_total",
    "post_reactions_wow_total",
    "post_reactions_haha_total",
    "post_reactions_sorry_total",
    "post_reactions_anger_total",
})

# Unavailability reason codes (machine-readable; consumed by Story 24-3)
_REASON_PAGE_UNDER_100_LIKES = "page_under_100_likes"
_REASON_PERMISSION_MISSING = "permission_missing"
_REASON_NO_DATA_YET = "no_data_yet"
_REASON_TOKEN_EXPIRED = "token_expired"
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
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    raw: dict = field(default_factory=dict)
    unavailable_reason: Optional[str] = None


# ── Shared component extraction ────────────────────────────────────────────────

def extract_components_from_raw(platform: str, raw: dict) -> tuple[Optional[int], Optional[int], Optional[int]]:
    """Derive (likes, comments, shares) from a stored raw JSONB payload.

    This is the single authoritative mapping used by both the live integration
    (MetricSnapshot construction) and the Alembic migration backfill so neither
    can drift. Never fabricates a zero — an absent field returns None (-> NULL).

    For Facebook, comments/shares come from raw["_object"] (the second object-edge
    call result stored alongside the insights data). Pre-24.4 rows without that key
    will have NULL comments/shares after backfill — that is correct.
    """
    if not isinstance(raw, dict) or not raw.get("data"):
        return None, None, None

    if platform == "facebook_page":
        # likes = sum of all individual post_reactions_*_total counters (see _FB_REACTION_METRICS).
        # post_reactions_by_type_total is deprecated (June 2026); use per-type counters.
        reaction_total = 0
        has_any_reaction = False
        for item in raw.get("data", []):
            if item.get("name") in _FB_REACTION_METRICS:
                values = item.get("values", [])
                val = values[0].get("value", 0) if values and isinstance(values[0], dict) else 0
                v = _int_or_none(val)
                if v is not None:
                    reaction_total += v
                    has_any_reaction = True
        likes = reaction_total if has_any_reaction else None
        obj = raw.get("_object", {})
        comments = None
        shares = None
        if obj:
            c = (obj.get("comments") or {}).get("summary", {}).get("total_count")
            if c is not None:
                comments = _int_or_none(c)
            s = (obj.get("shares") or {}).get("count")
            if s is not None:
                shares = _int_or_none(s)
        return likes, comments, shares

    if platform == "instagram":
        m = _ig_metrics_dict(raw)
        likes = m["likes"] if "likes" in m else None
        comments = m["comments"] if "comments" in m else None
        shares = m["shares"] if "shares" in m else None
        return likes, comments, shares

    if platform == "threads":
        m = _threads_metrics_dict(raw)
        likes = m["likes"] if "likes" in m else None
        comments = m["replies"] if "replies" in m else None
        shares = m["reposts"] if "reposts" in m else None
        return likes, comments, shares

    return None, None, None


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
        f"{META_GRAPH_BASE}/{post.platform_post_id}/insights",
        params={"metric": _FB_METRICS, "access_token": token},
    )
    raw = _safe_json(resp)

    if resp.status_code != 200:
        reason = _fb_unavailable_reason(raw.get("error") or {})
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
        logger.warning("meta_metrics FB unexpected non-200 post=%s status=%s body=%s", post.platform_post_id, resp.status_code, raw)
        resp.raise_for_status()

    # Second fault-isolated call for comments + shares (object-edge fields, not insights).
    # On failure: log + continue; primary snapshot is still recorded (AD-A10).
    obj_data: dict = {}
    try:
        obj_resp = await client.get(
            f"{META_GRAPH_BASE}/{post.platform_post_id}",
            params={"fields": "comments.summary(true),shares", "access_token": token},
        )
        if obj_resp.status_code == 200:
            obj_data = _safe_json(obj_resp)
        else:
            logger.warning(
                "meta_metrics FB object-edge call non-200 post=%s status=%s",
                post.platform_post_id,
                obj_resp.status_code,
            )
    except Exception as obj_exc:
        logger.warning(
            "meta_metrics FB object-edge call failed post=%s: %s",
            post.platform_post_id,
            obj_exc,
        )

    # Merge object-edge data into raw under "_object" key for storage and backfill parity.
    if obj_data:
        raw = {**raw, "_object": obj_data}

    return _map_facebook_snapshot(post, raw, now)


def _fb_unavailable_reason(error: dict) -> Optional[str]:
    """Map a Meta API error dict to a machine-readable unavailability reason.

    Returns None if the error is transient (should be raised, not recorded as unavailable).

    UNCERTAINTY — subcode 33: Meta docs describe code=100, subcode=33 as
    "Object with ID does not exist, cannot be loaded due to missing permissions,
    or does not support this operation" — a generic object-not-found/permission error,
    NOT the under-100-likes condition. The genuine under-100-likes condition surfaces
    as empty/zero insight data or a distinct message, not subcode 33. We cannot verify
    this against a real response in the sandbox right now, so the original mapping is
    preserved below but clearly marked. A Sentry breadcrumb captures the raw error body
    to settle this from production data (AC #12).
    """
    code = error.get("code")
    subcode = error.get("error_subcode")

    # UNCERTAIN: subcode 33 may be object-not-found/permission, not under-100-likes.
    # See docstring above. Preserve original mapping pending production verification.
    if code == 100 and subcode == 33:
        sentry_sdk.add_breadcrumb(
            category="meta_metrics",
            message="FB error code=100 subcode=33 hit — verify whether this is truly under-100-likes or object-not-found",
            data={"error": error},
            level="warning",
        )
        return _REASON_PAGE_UNDER_100_LIKES
    # Permission not granted (read_insights missing)
    if code == 10 or code == 200:
        return _REASON_PERMISSION_MISSING
    # Post too new / no data collected yet
    if code == 100 and subcode == 2108006:
        return _REASON_NO_DATA_YET
    # Token expired / invalid — record as unavailable; client must re-auth to recover
    if code == 190:
        return _REASON_TOKEN_EXPIRED
    # Unknown unavailability or non-standard error body — record rather than raise so sweep continues
    return _REASON_UNKNOWN


def _map_facebook_snapshot(post, raw: dict, now: datetime) -> MetricSnapshot:
    """Map a FB insights API response to normalized columns (post-June-2026-deprecation).

    raw["data"] is a list of {name, values} dicts. Each metric has a list of
    values with {value, end_time}; we take the first (most recent period).
    raw["_object"] (if present) carries comments.summary and shares from the
    second object-edge call (see _fetch_facebook).

    impressions <- post_media_view if present in data, else NULL (primary expected outcome).
      post_media_view is a speculative probe — Meta removed per-post impressions in June 2026.
      NULL impressions is NOT an unavailable row: engagements are still real and recorded.
      Do not set unavailable_reason for NULL impressions.

    likes <- sum(_FB_REACTION_METRICS counters) — individual integers, summed.
    engagements <- reactions + comments + shares (NULL-safe; no post_engaged_users anymore).
    """
    metrics_by_name: dict[str, object] = {}
    for item in raw.get("data", []):
        name = item.get("name", "")
        values = item.get("values", [{}])
        val = values[0].get("value", 0) if values and isinstance(values[0], dict) else 0
        metrics_by_name[name] = val

    # Impressions: probe candidate post_media_view; NULL is the primary expected outcome.
    impressions = _int_or_none(metrics_by_name.get("post_media_view"))

    # likes = sum of all individual reaction counters (see _FB_REACTION_METRICS).
    reaction_total = sum(
        _int_or_none(metrics_by_name.get(m)) or 0
        for m in _FB_REACTION_METRICS
    )
    likes_from_reactions = reaction_total or None

    # comments and shares come from the object-edge call stored in raw["_object"].
    _, comments, shares = extract_components_from_raw("facebook_page", raw)
    likes = likes_from_reactions

    # engagements = reactions + comments + shares (NULL-safe; no fabricated zeros).
    engagement_total = (likes or 0) + (comments or 0) + (shares or 0)
    engagements = engagement_total or None

    return MetricSnapshot(
        published_post_id=post.id,
        client_id=post.client_id,
        platform="facebook_page",
        captured_at=now,
        impressions=impressions,
        engagements=engagements,
        likes=likes,
        comments=comments,
        shares=shares,
        raw=raw,
    )


# ── Instagram ─────────────────────────────────────────────────────────────────

async def _fetch_instagram(client, post, creds: dict, now: datetime) -> MetricSnapshot:
    token = creds["page_access_token"]
    resp = await client.get(
        f"{META_GRAPH_BASE}/{post.platform_post_id}/insights",
        params={"metric": _IG_METRICS, "access_token": token},
    )
    raw = _safe_json(resp)

    if resp.status_code != 200:
        reason = _ig_unavailable_reason(raw.get("error") or {})
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
        logger.warning("meta_metrics IG unexpected non-200 post=%s status=%s body=%s", post.platform_post_id, resp.status_code, raw)
        resp.raise_for_status()

    return _map_instagram_snapshot(post, raw, now)


def _ig_unavailable_reason(error: dict) -> Optional[str]:
    code = error.get("code")
    if code == 10 or code == 200:
        return _REASON_PERMISSION_MISSING
    if code == 100:
        return _REASON_NO_DATA_YET
    if code == 190:
        return _REASON_TOKEN_EXPIRED
    return _REASON_UNKNOWN


def _map_instagram_snapshot(post, raw: dict, now: datetime) -> MetricSnapshot:
    """Map an IG insights API response to normalized columns.

    impressions <- views (IG v21+ replacement for the removed `impressions` metric)
                   fallback to reach if views absent.
    engagements <- likes + comments + saved + shares
    likes/comments/shares <- individual IG fields (saves not promoted, stays in engagements + raw)
    """
    m = _ig_metrics_dict(raw)

    impressions = m.get("views") or m.get("reach") or None
    engagements = (
        (m.get("likes") or 0)
        + (m.get("comments") or 0)
        + (m.get("saved") or 0)
        + (m.get("shares") or 0)
    ) or None

    likes, comments, shares = extract_components_from_raw("instagram", raw)

    return MetricSnapshot(
        published_post_id=post.id,
        client_id=post.client_id,
        platform="instagram",
        captured_at=now,
        impressions=impressions,
        engagements=engagements,
        likes=likes,
        comments=comments,
        shares=shares,
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
    # Threads uses user_access_token (not page_access_token).
    # Requires threads_manage_insights permission.
    # Host: graph.threads.com/v1.0 (NOT graph.facebook.com — Threads tokens are invalid there).
    token = creds["user_access_token"]
    resp = await client.get(
        f"{THREADS_GRAPH_BASE}/{post.platform_post_id}/insights",
        params={"metric": _THREADS_METRICS, "access_token": token},
    )
    raw = _safe_json(resp)

    if resp.status_code != 200:
        reason = _threads_unavailable_reason(raw.get("error") or {})
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
        logger.warning("meta_metrics Threads unexpected non-200 post=%s status=%s body=%s", post.platform_post_id, resp.status_code, raw)
        resp.raise_for_status()

    return _map_threads_snapshot(post, raw, now)


def _threads_unavailable_reason(error: dict) -> Optional[str]:
    code = error.get("code")
    if code == 10 or code == 200:
        return _REASON_PERMISSION_MISSING
    if code == 100:
        return _REASON_NO_DATA_YET
    if code == 190:
        return _REASON_TOKEN_EXPIRED
    return _REASON_UNKNOWN


def _map_threads_snapshot(post, raw: dict, now: datetime) -> MetricSnapshot:
    """Map a Threads insights API response to normalized columns.

    impressions <- views
    engagements <- likes + replies + reposts + quotes
    likes       <- likes
    comments    <- replies  (Threads vocab: replies = comments)
    shares      <- reposts  (Threads vocab: reposts = shares)
    Field names verified against Threads API Aug 2026; re-verify on Meta changelog updates.
    """
    m = _threads_metrics_dict(raw)

    impressions = m.get("views") or None
    engagements = (
        (m.get("likes") or 0)
        + (m.get("replies") or 0)
        + (m.get("reposts") or 0)
        + (m.get("quotes") or 0)
    ) or None

    likes, comments, shares = extract_components_from_raw("threads", raw)

    return MetricSnapshot(
        published_post_id=post.id,
        client_id=post.client_id,
        platform="threads",
        captured_at=now,
        impressions=impressions,
        engagements=engagements,
        likes=likes,
        comments=comments,
        shares=shares,
        raw=raw,
    )


def _threads_metrics_dict(raw: dict) -> dict[str, int]:
    """Parse Threads insights payload into a name->int mapping.

    Threads insights uses the same list form as FB/IG:
      {"data": [{"name": "likes", "values": [{"value": 100}]}, ...]}
    NOT the flat {"name": "likes", "value": 100} form.
    Read values[0].value (list form) — the old item.get("value") path was wrong.
    """
    result: dict[str, int] = {}
    for item in raw.get("data", []):
        name = item.get("name", "")
        values = item.get("values", [])
        val = values[0].get("value", 0) if values and isinstance(values[0], dict) else 0
        result[name] = int(val) if val else 0
    return result


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_json(resp: httpx.Response) -> dict:
    try:
        return resp.json()
    except Exception:
        return {"_raw_text": resp.text[:500]}


def _int_or_none(val) -> Optional[int]:
    if val is None:
        return None
    if isinstance(val, dict):
        total = sum(v for v in val.values() if isinstance(v, int))
        return total or None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None
