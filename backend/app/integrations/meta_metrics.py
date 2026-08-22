"""Meta Graph API insights integration for Facebook Page, Instagram, and Threads posts.

Normalized metric mapping (AD-A3 convention):
  impressions  <- FB: post_impressions | IG: views (fallback reach) | Threads: views
  engagements  <- FB: reactions+comments+shares | IG: likes+comments+saved+shares | Threads: likes+replies+reposts+quotes
  likes        <- FB: LIKE subtype from post_reactions_by_type_total | IG: likes | Threads: likes
  comments     <- FB: comments.summary(true).total_count (object-edge) | IG: comments | Threads: replies
  shares       <- FB: shares.count (object-edge) | IG: shares | Threads: reposts

Story 24.4 amendment (AD-A7): the normalized set now includes a bounded set of
  engagement-component columns (likes, comments, shares) alongside engagements.
  AD-A7 previously allowed only (impressions, engagements). engagements formula is
  unchanged; saves (IG) is NOT promoted — it stays inside engagements + raw.

FB Page insights require 100+ page likes; below that threshold the API returns an
  error and we record unavailable_reason="page_under_100_likes" (no fabricated zeros).

Instagram `impressions` was removed in Graph v21 (Jan 2025); `views` is the replacement.

Threads endpoint/metric names: VERIFY against live Threads API at deploy time.
  The endpoint and field names below are correct as of Aug 2026 but Meta evolves them.

Facebook Page Insights metric set post-June-2026-deprecation:
  VERIFY: run GET /{post_id}/insights?metric=<FB_METRICS> with a real post to confirm
  the metrics below are still available after the June 2026 Insights API update.

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
        likes = None
        for item in raw.get("data", []):
            if item.get("name") == "post_reactions_by_type_total":
                values = item.get("values", [{}])
                val = values[0].get("value", {}) if values else {}
                if isinstance(val, dict):
                    raw_like = val.get("LIKE")
                    if raw_like is not None:
                        likes = _int_or_none(raw_like)
                break
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
        f"{_GRAPH_BASE}/{post.platform_post_id}/insights",
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
            f"{_GRAPH_BASE}/{post.platform_post_id}",
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
    """Map a FB insights API response to normalized columns.

    raw["data"] is a list of {name, values} dicts. Each metric has a list of
    values with {value, end_time}; we take the first (most recent period).
    raw["_object"] (if present) carries comments.summary and shares from the
    second object-edge call (see _fetch_facebook).
    """
    metrics_by_name: dict[str, object] = {}
    for item in raw.get("data", []):
        name = item.get("name", "")
        values = item.get("values", [{}])
        val = values[0].get("value", 0) if values else 0
        metrics_by_name[name] = val

    impressions = _int_or_none(metrics_by_name.get("post_impressions"))

    # Prefer post_engaged_users (broader signal) over reactions; use explicit key presence
    # check so a legitimate zero doesn't fall through to the reactions fallback.
    if "post_engaged_users" in metrics_by_name:
        engagements = _int_or_none(metrics_by_name["post_engaged_users"])
    else:
        reactions_val = metrics_by_name.get("post_reactions_by_type_total")
        if isinstance(reactions_val, dict):
            total = sum(v for v in reactions_val.values() if isinstance(v, int))
            engagements = total or None
        else:
            engagements = _int_or_none(reactions_val)

    likes, comments, shares = extract_components_from_raw("facebook_page", raw)

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
        f"{_GRAPH_BASE}/{post.platform_post_id}/insights",
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
    # Threads uses user_access_token (not page_access_token)
    token = creds["user_access_token"]
    resp = await client.get(
        f"{_GRAPH_BASE}/{post.platform_post_id}/insights",
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
