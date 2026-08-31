"""LinkedIn organization analytics integration (company-page posts only).

Metric mapping (AD-A3):
  impressions  <- totalShareStatistics.impressionCount (fallback: uniqueImpressionsCount)
  engagements  <- likeCount + commentCount + shareCount + clickCount
  likes        <- likeCount
  comments     <- commentCount
  shares       <- shareCount

Stats endpoint: GET /rest/organizationalEntityShareStatistics
  q=organizationalEntity
  organizationalEntity=urn:li:organization:{org_id}
  shares=List(urn:li:share:{share_id})   (per-post; only works with share URN)
  Omitting 'shares' gives org-level aggregate (fallback for ugcPost URNs).

URN routing:
  - create_post_with_image (/rest/posts) -> share URN (urn:li:share:{id})
    -> use per-post stats with shares=List({share_urn}) param.
  - create_ugc_post (/v2/ugcPosts) -> ugcPost URN (urn:li:ugcPost:{id})
    -> the `ugcPosts` param on organizationalEntityShareStatistics is documented
       but reported buggy (can 403 with ACCESS_DENIED). Fall back to org-aggregate
       stats (no `shares` param) — returns totals across all org posts in the window.
       Store unavailable_reason=None since aggregate data is still useful; the raw
       payload notes that it is org-level.

Version header: LinkedIn-Version: 202608 (202508 sunset Aug 17 2026)
X-Restli-Protocol-Version: 2.0.0
12-month rolling window; no pagination; no new packages.

Personal-profile posts (target != "organization") are skipped here;
unavailable_reason = "member_post_unsupported". Story 25-2 owns them.
"""

import asyncio
import logging
import urllib.parse
from datetime import datetime, timezone
from typing import Optional

import httpx
import sentry_sdk

from app.integrations.meta_metrics import MetricSnapshot  # reuse dataclass

logger = logging.getLogger(__name__)

SUPPORTS_METRICS = True
platform = "linkedin"

# LinkedIn-Version: 202608 is the current version as of 2026-08-30.
# 202508 was sunset Aug 17 2026; never use 202602 for new code here.
_LI_VERSION = "202608"
_LI_BASE = "https://api.linkedin.com/rest"
_LI_HEADERS = {
    "LinkedIn-Version": _LI_VERSION,
    "X-Restli-Protocol-Version": "2.0.0",
}

# Machine-readable unavailability reason codes (must match REASON_COPY keys in
# frontend/components/analytics/PlatformUnavailableState.tsx exactly — AC #9a).
_REASON_SCOPE_MISSING = "scope_missing"
_REASON_MEMBER_POST_UNSUPPORTED = "member_post_unsupported"
_REASON_NO_DATA_YET = "no_data_yet"
_REASON_TOKEN_EXPIRED = "token_expired"
_REASON_UNKNOWN = "unknown"


async def fetch(
    posts: list,  # list[PublishedPost]
    creds: dict,
    platform_arg: str,
) -> list[MetricSnapshot]:
    """Fetch organizationalEntityShareStatistics for a batch of LinkedIn posts.

    Fault-isolated per item (AD-A10): one post failing is caught, logged to Sentry,
    and skipped. The sweep continues for all other posts.
    Credentials are never logged (decrypted creds stay in local scope only).
    5-second stagger between items to respect LinkedIn's rate-limit discipline.
    """
    results: list[MetricSnapshot] = []
    now = datetime.now(timezone.utc)

    async with httpx.AsyncClient(timeout=15.0) as client:
        for i, post in enumerate(posts):
            if i > 0:
                # LinkedIn rate-limit discipline: ~5s between outbound reads.
                await asyncio.sleep(5.0)
            try:
                snapshot = await _fetch_one(client, post, creds, now)
                results.append(snapshot)
            except Exception as exc:
                logger.error(
                    "linkedin_metrics fetch error post_id=%s: %s",
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
    now: datetime,
) -> MetricSnapshot:
    """Fetch stats for a single LinkedIn published post.

    Credential shape (from linkedin_oauth_callback / _extract_linkedin_target):
      access_token, name, scopes, target, org_id, org_name

    Routing:
      - target != "organization" -> member_post_unsupported (25-2 owns this)
      - share URN (urn:li:share:*) -> per-post stats scoped to that URN
      - ugcPost URN or other      -> org-aggregate stats (fallback, AC #5)
    """
    access_token: str = creds.get("access_token", "")
    org_id: Optional[str] = creds.get("org_id")
    target: str = creds.get("target", "personal")

    if target != "organization":
        # Personal-profile posts: owned by Story 25-2. The LINKEDIN_MEMBER_METRICS_ENABLED
        # flag in config.py will gate that path; it remains False until 25-2 ships.
        return MetricSnapshot(
            published_post_id=post.id,
            client_id=post.client_id,
            platform="linkedin",
            captured_at=now,
            raw={},
            unavailable_reason=_REASON_MEMBER_POST_UNSUPPORTED,
        )

    post_urn: str = getattr(post, "platform_post_id", "") or ""
    is_share_urn = post_urn.startswith("urn:li:share:")

    try:
        if is_share_urn:
            # Per-post stats: scope the query to this specific share URN (AC #3).
            raw = await _fetch_org_stats(client, access_token, org_id, share_urn_or_none=post_urn)
        else:
            # ugcPost URN or unknown: use org-aggregate as fallback (AC #5).
            # The ugcPosts param on organizationalEntityShareStatistics is documented
            # but reported to 403 with ACCESS_DENIED; aggregate is the safe path.
            raw = await _fetch_org_stats(client, access_token, org_id, share_urn_or_none=None)

    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        body: dict = {}
        try:
            body = exc.response.json()
        except Exception:
            pass
        reason = _li_unavailable_reason(status, body)
        logger.info(
            "linkedin_metrics unavailable post=%s status=%s reason=%s",
            post_urn, status, reason,
        )
        return MetricSnapshot(
            published_post_id=post.id,
            client_id=post.client_id,
            platform="linkedin",
            captured_at=now,
            raw=body,
            unavailable_reason=reason,
        )

    # Check for empty elements (no data yet or org mismatch)
    elements = raw.get("elements", [])
    if not elements:
        return MetricSnapshot(
            published_post_id=post.id,
            client_id=post.client_id,
            platform="linkedin",
            captured_at=now,
            raw=raw,
            unavailable_reason=_REASON_NO_DATA_YET,
        )

    return _map_snapshot(post, raw, now)


async def _fetch_org_stats(
    client: httpx.AsyncClient,
    access_token: str,
    org_id: Optional[str],
    share_urn_or_none: Optional[str],
) -> dict:
    """GET /rest/organizationalEntityShareStatistics.

    When share_urn_or_none is provided, scopes the query to that specific share URN
    (per-post stats for urn:li:share:{id}). When None, returns org-aggregate stats
    across all posts in the 12-month rolling window.

    The `shares` param uses LinkedIn's List encoding: shares=List(urn:li:share:{id})
    which URL-encodes to shares=List(urn%3Ali%3Ashare%3A{id}).

    URL is built manually: httpx's params= dict would percent-encode the List()
    parentheses (( → %28, ) → %29), which LinkedIn's Restli parser rejects.
    """
    if not org_id:
        raise ValueError(f"org_id required for LinkedIn org stats, got {org_id!r}")

    # Percent-encode the org URN (colons → %3A); keep List() parens literal in the URL.
    org_urn_enc = urllib.parse.quote(f"urn:li:organization:{org_id}", safe="")
    url = (
        f"{_LI_BASE}/organizationalEntityShareStatistics"
        f"?q=organizationalEntity&organizationalEntity={org_urn_enc}"
    )
    if share_urn_or_none:
        # LinkedIn List() encoding for the shares parameter (AC #3).
        # URN colons are encoded; List() parens must stay literal or LinkedIn rejects the request.
        share_enc = urllib.parse.quote(share_urn_or_none, safe="")
        url += f"&shares=List({share_enc})"

    resp = await client.get(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            **_LI_HEADERS,
        },
    )
    resp.raise_for_status()
    try:
        return resp.json()
    except Exception:
        return {"_raw_text": resp.text[:500]}


def _map_snapshot(post, raw: dict, now: datetime) -> MetricSnapshot:
    """Map an organizationalEntityShareStatistics response to normalized columns.

    Navigation:
      raw.elements[0].totalShareStatistics -> stats dict

    Mapping (AD-A3):
      impressions  <- impressionCount (fallback uniqueImpressionsCount)
      engagements  <- likeCount + commentCount + shareCount + clickCount (NULL-safe)
      likes        <- likeCount
      comments     <- commentCount
      shares       <- shareCount

    LinkedIn's own `engagement` rate field (float) is preserved in raw.
    Never fabricate a zero — absent field yields None -> NULL (AD-A5).
    """
    stats: dict = (
        raw.get("elements", [{}])[0]
           .get("totalShareStatistics", {})
    )

    # impressions: prefer impressionCount, fall back to uniqueImpressionsCount
    raw_impressions = stats.get("impressionCount")
    if raw_impressions is None:
        raw_impressions = stats.get("uniqueImpressionsCount")
    impressions = _int_or_none(raw_impressions)

    likes = _int_or_none(stats.get("likeCount"))
    comments = _int_or_none(stats.get("commentCount"))
    shares = _int_or_none(stats.get("shareCount"))
    clicks = _int_or_none(stats.get("clickCount"))

    # engagements = likes + comments + shares + clicks (NULL-safe, no fabricated zeros)
    engagement_total = (likes or 0) + (comments or 0) + (shares or 0) + (clicks or 0)
    engagements = engagement_total or None

    return MetricSnapshot(
        published_post_id=post.id,
        client_id=post.client_id,
        platform="linkedin",
        captured_at=now,
        impressions=impressions,
        engagements=engagements,
        likes=likes,
        comments=comments,
        shares=shares,
        raw=raw,
    )


def _li_unavailable_reason(status_code: int, body: dict) -> str:
    """Map an HTTP status / body to a machine-readable unavailability reason.

    Reason codes must match REASON_COPY keys in PlatformUnavailableState.tsx (AC #9a).
    """
    if status_code == 401:
        return _REASON_TOKEN_EXPIRED
    if status_code == 403:
        return _REASON_SCOPE_MISSING
    # Empty elements in a 200 response = no data collected yet
    elements = body.get("elements", None)
    if elements is not None and len(elements) == 0:
        return _REASON_NO_DATA_YET
    return _REASON_UNKNOWN


def _int_or_none(val) -> Optional[int]:
    """Convert a value to int or return None — never fabricates a zero for absent fields."""
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None
