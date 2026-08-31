"""LinkedIn post analytics integration (company-page org path + personal-profile member path).

Two branches, selected by the connection's stored `target`:
  - target == "organization" -> org path: organizationalEntityShareStatistics (Story 25.1)
  - target != "organization" -> member path: memberCreatorPostAnalytics (Story 25.2)

Org metric mapping (AD-A3):
  impressions  <- totalShareStatistics.impressionCount (fallback: uniqueImpressionsCount)
  engagements  <- likeCount + commentCount + shareCount + clickCount
  likes        <- likeCount
  comments     <- commentCount
  shares       <- shareCount

Member metric mapping (AD-A3, Story 25.2):
  impressions  <- IMPRESSION (fallback: MEMBERS_REACHED)
  engagements  <- REACTION + COMMENT + RESHARE + POST_SAVE + LINK_CLICKS (NULL-safe)
  likes        <- REACTION
  comments     <- COMMENT
  shares       <- RESHARE
  All member metric counts (incl. POST_SEND, FOLLOWER_GAINED_FROM_CONTENT,
  PROFILE_VIEW_FROM_CONTENT) are preserved in raw.memberCreatorPostAnalytics.

Member endpoint: GET /rest/memberCreatorPostAnalytics
  q=entity
  entity=(share:urn%3Ali%3Ashare%3A{id})   for share URNs
  entity=(ugc:urn%3Ali%3AugcPost%3A{id})   for ugcPost URNs
  queryType={METRIC}   one metric per call — the finder returns a single metric type,
                       so a full snapshot fans out to one GET per metric (aggregation=TOTAL).
  aggregation=TOTAL    single lifetime data point per metric.
  Scope: r_member_postAnalytics. Gated by LINKEDIN_MEMBER_METRICS_ENABLED (default False).
  Response (li-lms-2026-08): elements[].count + flat elements[].metricType string.

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

Version header: LinkedIn-Version: 202608 (li-lms-2026-08). Applies to both branches.
"""

import asyncio
import logging
import urllib.parse
from datetime import datetime, timezone
from typing import Optional

import httpx
import sentry_sdk

from app.core.config import settings
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
_REASON_NO_DATA_YET = "no_data_yet"
_REASON_TOKEN_EXPIRED = "token_expired"
_REASON_UNKNOWN = "unknown"
# Member-path reason codes (Story 25.2). Same parity contract with the frontend.
_REASON_MEMBER_DISABLED = "member_metrics_disabled"      # feature flag off
_REASON_MEMBER_SCOPE_MISSING = "member_scope_missing"    # connection predates the scope grant
_REASON_CONSENT_REVOKED = "consent_revoked"              # scope present, LinkedIn denies analytics

# Member analytics scope (memberCreatorPostAnalytics). See frontend authorize URL.
_MEMBER_SCOPE = "r_member_postAnalytics"

# Metric types fetched per personal post (AC #4). The finder returns one metric per call,
# so this list is the fan-out. Order is irrelevant; all counts land in raw.
# IMPRESSION/MEMBERS_REACHED feed impressions; REACTION/COMMENT/RESHARE/POST_SAVE/LINK_CLICKS
# feed engagements; the remainder are preserved in raw only.
_MEMBER_METRIC_TYPES = (
    "IMPRESSION",
    "MEMBERS_REACHED",
    "REACTION",
    "COMMENT",
    "RESHARE",
    "POST_SAVE",
    "LINK_CLICKS",
    "POST_SEND",
    "FOLLOWER_GAINED_FROM_CONTENT",
    "PROFILE_VIEW_FROM_CONTENT",
)


async def fetch(
    posts: list,  # list[PublishedPost]
    creds: dict,
    platform_arg: str,
) -> list[MetricSnapshot]:
    """Fetch analytics for a batch of LinkedIn posts (org or member path per connection target).

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

    Routing (AC #6):
      - target != "organization" -> member path (Story 25.2), flag + scope gated
      - share URN (urn:li:share:*) -> per-post org stats scoped to that URN
      - ugcPost URN or other      -> org-aggregate stats (fallback, AC #5)
    """
    access_token: str = creds.get("access_token", "")
    org_id: Optional[str] = creds.get("org_id")
    target: str = creds.get("target", "personal")

    if target != "organization":
        # Personal-profile posts route to the member path (Story 25.2).
        return await _fetch_member_one(client, post, creds, now)

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


# ── Member path (personal-profile posts, Story 25.2) ──────────────────────────

async def _fetch_member_one(
    client: httpx.AsyncClient,
    post,
    creds: dict,
    now: datetime,
) -> MetricSnapshot:
    """Fetch memberCreatorPostAnalytics for a single personal-profile post.

    Gating (AC #1, #2):
      - LINKEDIN_MEMBER_METRICS_ENABLED False -> member_metrics_disabled (no API call)
      - connection lacks r_member_postAnalytics -> member_scope_missing (no API call)
    Both keep the 25-1 "not available" state; the frontend surfaces a reconnect hint.

    Fault isolation (AD-A10): an auth/consent failure (401/403) degrades the whole post to
    an unavailable snapshot; a transient/unsupported failure on a single metric (400/500) is
    skipped so the remaining metrics still produce a snapshot. Never raises to the caller.
    """
    if not settings.LINKEDIN_MEMBER_METRICS_ENABLED:
        return _member_unavailable(post, now, _REASON_MEMBER_DISABLED, {})

    scopes = creds.get("scopes") or ""
    if _MEMBER_SCOPE not in scopes:
        return _member_unavailable(post, now, _REASON_MEMBER_SCOPE_MISSING, {})

    access_token: str = creds.get("access_token", "")
    post_urn: str = getattr(post, "platform_post_id", "") or ""
    entity_param = _member_entity_param(post_urn)
    if entity_param is None:
        # Neither a share nor a ugcPost URN — nothing the member finder can key on.
        logger.info("member metrics: unroutable URN post=%s", post_urn)
        return _member_unavailable(post, now, _REASON_UNKNOWN, {})

    counts: dict[str, int] = {}
    for metric in _MEMBER_METRIC_TYPES:
        try:
            count = await _fetch_member_metric(client, access_token, entity_param, metric)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status in (401, 403):
                # Auth/consent failure affects every metric for this post — stop and record it.
                body = _safe_json(exc.response)
                reason = _member_unavailable_reason(status, body)
                logger.info(
                    "member metrics unavailable post=%s status=%s reason=%s",
                    post_urn, status, reason,
                )
                return _member_unavailable(post, now, reason, body)
            # Transient/unsupported single metric: skip it, keep the rest (AD-A10).
            logger.info(
                "member metric %s failed status=%s post=%s (skipped)",
                metric, status, post_urn,
            )
            continue
        if count is not None:
            counts[metric] = count

    if not counts:
        return _member_unavailable(post, now, _REASON_NO_DATA_YET, {})

    return _map_member_snapshot(post, counts, now)


async def _fetch_member_metric(
    client: httpx.AsyncClient,
    access_token: str,
    entity_param: str,
    metric: str,
) -> Optional[int]:
    """GET a single member metric total for one post. Returns the count or None.

    URL is built manually: LinkedIn's Restli entity finder needs the literal parentheses
    of entity=(share:...) / entity=(ugc:...) — httpx's params= dict would percent-encode
    them and the parser would reject the request.
    """
    url = (
        f"{_LI_BASE}/memberCreatorPostAnalytics"
        f"?q=entity&entity={entity_param}"
        f"&queryType={metric}&aggregation=TOTAL"
    )
    resp = await client.get(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            **_LI_HEADERS,
        },
    )
    resp.raise_for_status()
    body = _safe_json(resp)
    elements = body.get("elements", [])
    if not elements:
        return None
    # aggregation=TOTAL yields one element; sum defensively if the API returns more.
    total = 0
    found = False
    for el in elements:
        c = _int_or_none(el.get("count"))
        if c is not None:
            total += c
            found = True
    return total if found else None


def _member_entity_param(post_urn: str) -> Optional[str]:
    """Build the memberCreatorPostAnalytics `entity` value for a post URN.

    share URN   -> (share:{urn-encoded})
    ugcPost URN -> (ugc:{urn-encoded})   (the finder keys ugcPost URNs under `ugc`)
    """
    if not post_urn:
        return None
    enc = urllib.parse.quote(post_urn, safe="")
    if post_urn.startswith("urn:li:share:"):
        return f"(share:{enc})"
    if post_urn.startswith("urn:li:ugcPost:"):
        return f"(ugc:{enc})"
    return None


def _map_member_snapshot(post, counts: dict, now: datetime) -> MetricSnapshot:
    """Map collected memberCreatorPostAnalytics counts to normalized columns (AC #4).

    impressions <- IMPRESSION (fallback MEMBERS_REACHED)
    engagements <- REACTION + COMMENT + RESHARE + POST_SAVE + LINK_CLICKS (NULL-safe)
    likes       <- REACTION
    comments    <- COMMENT
    shares      <- RESHARE
    All raw counts (incl. POST_SEND, FOLLOWER_GAINED_FROM_CONTENT, PROFILE_VIEW_FROM_CONTENT)
    are preserved under raw.memberCreatorPostAnalytics. Absent metrics stay None (AD-A5).
    """
    impressions = counts.get("IMPRESSION")
    if impressions is None:
        impressions = counts.get("MEMBERS_REACHED")

    reactions = _int_or_none(counts.get("REACTION"))
    comments = _int_or_none(counts.get("COMMENT"))
    reshares = _int_or_none(counts.get("RESHARE"))
    post_saves = _int_or_none(counts.get("POST_SAVE"))
    link_clicks = _int_or_none(counts.get("LINK_CLICKS"))

    engagement_total = (
        (reactions or 0) + (comments or 0) + (reshares or 0)
        + (post_saves or 0) + (link_clicks or 0)
    )
    engagements = engagement_total or None

    return MetricSnapshot(
        published_post_id=post.id,
        client_id=post.client_id,
        platform="linkedin",
        captured_at=now,
        impressions=_int_or_none(impressions),
        engagements=engagements,
        likes=reactions,
        comments=comments,
        shares=reshares,
        raw={"memberCreatorPostAnalytics": counts},
    )


def _member_unavailable(post, now: datetime, reason: str, raw: dict) -> MetricSnapshot:
    """Build an unavailability snapshot for a personal-profile post."""
    return MetricSnapshot(
        published_post_id=post.id,
        client_id=post.client_id,
        platform="linkedin",
        captured_at=now,
        raw=raw,
        unavailable_reason=reason,
    )


def _member_unavailable_reason(status_code: int, body: dict) -> str:
    """Map a member-path HTTP status / body to a machine-readable reason (AC #8).

    401 -> token_expired. 403 -> consent_revoked, unless the body names a scope/permission
    gap (then member_scope_missing). Everything else -> unknown.
    The connection-level scope is checked before any call, so a 403 here means the member
    revoked app consent or the Community Management product is not fully approved.
    """
    if status_code == 401:
        return _REASON_TOKEN_EXPIRED
    if status_code == 403:
        msg = str(body).lower()
        if "scope" in msg or "permission" in msg:
            return _REASON_MEMBER_SCOPE_MISSING
        return _REASON_CONSENT_REVOKED
    return _REASON_UNKNOWN


def _safe_json(resp: httpx.Response) -> dict:
    """Parse a response body as JSON, returning {} on failure."""
    try:
        parsed = resp.json()
        return parsed if isinstance(parsed, dict) else {"_raw": parsed}
    except Exception:
        return {}


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
