import uuid
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.analytics import (
    BestPost,
    ClientPostMetricsResponse,
    ClientSummaryResponse,
    PostMetricItem,
    SeriesPoint,
)

# Platforms that may produce metrics in this epic (Meta only for now)
_META_PLATFORMS = ("facebook_page", "instagram", "threads")


async def get_client_summary(
    session: AsyncSession,
    client_id: uuid.UUID,
) -> ClientSummaryResponse:
    """
    Compute client-level rollup from post_metrics via SQL only (AD-A2).
    Latest value per post = row with highest captured_at (DISTINCT ON, AD-A3).
    Never 500s on missing data (AD-A10).
    engagement_rate = SUM(engagements) / SUM(impressions), NULL-safe.
    """
    result = await session.execute(
        text("""
            WITH latest AS (
                SELECT DISTINCT ON (published_post_id)
                    published_post_id,
                    impressions,
                    engagements,
                    likes,
                    comments,
                    shares,
                    captured_at
                FROM post_metrics
                WHERE client_id = :client_id
                  AND platform = ANY(:platforms)
                ORDER BY published_post_id, captured_at DESC
            )
            SELECT
                COUNT(*) AS posts_tracked,
                SUM(impressions) AS total_impressions,
                SUM(engagements) AS total_engagements,
                SUM(likes) AS total_likes,
                SUM(comments) AS total_comments,
                SUM(shares) AS total_shares,
                CASE
                    WHEN SUM(impressions) > 0
                    THEN SUM(engagements)::float / SUM(impressions)::float
                    ELSE NULL
                END AS engagement_rate,
                MAX(captured_at) AS freshest_captured_at,
                (
                    SELECT published_post_id::text
                    FROM latest
                    ORDER BY engagements DESC NULLS LAST
                    LIMIT 1
                ) AS best_post_id
            FROM latest
        """),
        {"client_id": str(client_id), "platforms": list(_META_PLATFORMS)},
    )
    row = result.mappings().first()

    if not row or row["posts_tracked"] == 0:
        return ClientSummaryResponse(
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

    best_post: Optional[BestPost] = None
    best_post_id_str = row["best_post_id"]

    if best_post_id_str:
        bp_result = await session.execute(
            text("""
                SELECT
                    pp.id AS published_post_id,
                    pp.platform,
                    pp.permalink,
                    LEFT(c.brain_dump, 120) AS campaign_title,
                    pm.engagements
                FROM published_posts pp
                JOIN campaigns c ON c.id = pp.campaign_id
                JOIN LATERAL (
                    SELECT engagements
                    FROM post_metrics
                    WHERE published_post_id = pp.id
                    ORDER BY captured_at DESC
                    LIMIT 1
                ) pm ON TRUE
                WHERE pp.id = :ppid
            """),
            {"ppid": best_post_id_str},
        )
        bp_row = bp_result.mappings().first()
        if bp_row:
            best_post = BestPost(
                published_post_id=uuid.UUID(str(bp_row["published_post_id"])),
                platform=bp_row["platform"],
                campaign_title=bp_row["campaign_title"] or "(untitled)",
                engagements=bp_row["engagements"],
                permalink=bp_row["permalink"],
            )

    return ClientSummaryResponse(
        client_id=client_id,
        total_impressions=int(row["total_impressions"]) if row["total_impressions"] is not None else None,
        total_engagements=int(row["total_engagements"]) if row["total_engagements"] is not None else None,
        total_likes=int(row["total_likes"]) if row["total_likes"] is not None else None,
        total_comments=int(row["total_comments"]) if row["total_comments"] is not None else None,
        total_shares=int(row["total_shares"]) if row["total_shares"] is not None else None,
        engagement_rate=float(row["engagement_rate"]) if row["engagement_rate"] is not None else None,
        posts_tracked=int(row["posts_tracked"]),
        best_post=best_post,
        freshest_captured_at=row["freshest_captured_at"],
    )


async def get_client_post_metrics(
    session: AsyncSession,
    client_id: uuid.UUID,
) -> ClientPostMetricsResponse:
    """
    Return per-post metrics for all Meta published posts of a client.
    Latest snapshot = DISTINCT ON captured_at DESC (AD-A3).
    Posts with no snapshots return explicit unavailable marker (AD-A5).
    engagement_rate per post = engagements / impressions, NULL-safe (NULLIF).
    Never 500s (AD-A10).
    """
    # All published Meta posts for this client (joined with campaign info)
    posts_result = await session.execute(
        text("""
            SELECT
                pp.id AS published_post_id,
                pp.platform,
                pp.permalink,
                LEFT(c.brain_dump, 120) AS campaign_title,
                c.excerpt AS campaign_excerpt
            FROM published_posts pp
            JOIN campaigns c ON c.id = pp.campaign_id
            WHERE pp.client_id = :client_id
              AND pp.platform = ANY(:platforms)
            ORDER BY pp.created_at DESC
        """),
        {"client_id": str(client_id), "platforms": list(_META_PLATFORMS)},
    )
    posts = posts_result.mappings().all()

    if not posts:
        return ClientPostMetricsResponse(
            client_id=client_id,
            items=[],
            freshest_captured_at=None,
        )

    post_ids = [str(p["published_post_id"]) for p in posts]

    # Latest snapshot per post (bulk DISTINCT ON), including component columns
    latest_result = await session.execute(
        text("""
            SELECT DISTINCT ON (published_post_id)
                published_post_id,
                impressions,
                engagements,
                likes,
                comments,
                shares,
                CASE
                    WHEN NULLIF(impressions, 0) IS NOT NULL
                    THEN engagements::float / impressions::float
                    ELSE NULL
                END AS engagement_rate,
                captured_at,
                unavailable_reason
            FROM post_metrics
            WHERE published_post_id = ANY(:ids)
              AND client_id = :client_id
            ORDER BY published_post_id, captured_at DESC
        """),
        {"ids": post_ids, "client_id": str(client_id)},
    )
    latest_map: dict[str, dict] = {
        str(r["published_post_id"]): dict(r)
        for r in latest_result.mappings().all()
    }

    # Series for all posts (last 10 snapshots each for sparkline, asc order)
    series_result = await session.execute(
        text("""
            SELECT published_post_id, impressions, engagements, captured_at
            FROM (
                SELECT
                    published_post_id,
                    impressions,
                    engagements,
                    captured_at,
                    ROW_NUMBER() OVER (
                        PARTITION BY published_post_id
                        ORDER BY captured_at DESC
                    ) AS rn
                FROM post_metrics
                WHERE published_post_id = ANY(:ids)
                  AND client_id = :client_id
            ) ranked
            WHERE rn <= 10
            ORDER BY published_post_id, captured_at ASC
        """),
        {"ids": post_ids, "client_id": str(client_id)},
    )
    series_map: dict[str, list[SeriesPoint]] = {}
    for r in series_result.mappings().all():
        pid = str(r["published_post_id"])
        series_map.setdefault(pid, []).append(
            SeriesPoint(
                captured_at=r["captured_at"],
                impressions=r["impressions"],
                engagements=r["engagements"],
            )
        )

    # Freshest captured_at via SQL MAX (AD-A2 — no in-process aggregation)
    freshest_result = await session.execute(
        text(
            "SELECT MAX(captured_at) FROM post_metrics"
            " WHERE published_post_id = ANY(:ids) AND client_id = :client_id"
        ),
        {"ids": post_ids, "client_id": str(client_id)},
    )
    freshest = freshest_result.scalar()

    items: list[PostMetricItem] = []

    for post in posts:
        pid = str(post["published_post_id"])
        snap = latest_map.get(pid)

        if snap is None:
            items.append(
                PostMetricItem(
                    published_post_id=uuid.UUID(pid),
                    platform=post["platform"],
                    campaign_title=post["campaign_title"] or "(untitled)",
                    campaign_excerpt=post["campaign_excerpt"],
                    latest_impressions=None,
                    latest_engagements=None,
                    latest_likes=None,
                    latest_comments=None,
                    latest_shares=None,
                    engagement_rate=None,
                    permalink=post["permalink"],
                    captured_at=None,
                    series=[],
                    unavailable_reason="no_snapshot",
                )
            )
        else:
            items.append(
                PostMetricItem(
                    published_post_id=uuid.UUID(pid),
                    platform=post["platform"],
                    campaign_title=post["campaign_title"] or "(untitled)",
                    campaign_excerpt=post["campaign_excerpt"],
                    latest_impressions=int(snap["impressions"]) if snap["impressions"] is not None else None,
                    latest_engagements=int(snap["engagements"]) if snap["engagements"] is not None else None,
                    latest_likes=int(snap["likes"]) if snap["likes"] is not None else None,
                    latest_comments=int(snap["comments"]) if snap["comments"] is not None else None,
                    latest_shares=int(snap["shares"]) if snap["shares"] is not None else None,
                    engagement_rate=float(snap["engagement_rate"]) if snap["engagement_rate"] is not None else None,
                    permalink=post["permalink"],
                    captured_at=snap["captured_at"],
                    series=series_map.get(pid, []),
                    unavailable_reason=snap["unavailable_reason"],
                )
            )

    return ClientPostMetricsResponse(
        client_id=client_id,
        items=items,
        freshest_captured_at=freshest,
    )
