"""add_likes_comments_shares_to_post_metrics

Revision ID: 4789135e4739
Revises: f8a9b0c1d2e3
Create Date: 2026-08-21 22:51:38.930853

Story 24.4 — Architecture Spine Amendment AD-A7:
  Widens the normalized column set from (impressions, engagements) to also include
  (likes, comments, shares). engagements keeps its existing value/formula unchanged.
  AD-A3 (append-only) is preserved: these columns are populated at write time from a
  single API snapshot; the backfill below reads historical raw JSONB once and is
  idempotent (only fills NULL likes rows). No UPDATE path is introduced in normal operation.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4789135e4739'
down_revision: Union[str, Sequence[str], None] = 'f8a9b0c1d2e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _extract_components(platform: str, raw: dict):
    """Derive (likes, comments, shares) from a stored raw JSONB payload.

    Mirrors extract_components_from_raw() in meta_metrics so migration backfill
    and the live integration cannot drift. Never fabricates a zero — absent field
    stays NULL.

    Returns (None, None, None) for unavailability rows or unrecognised payloads.
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
                        try:
                            likes = int(raw_like)
                        except (TypeError, ValueError):
                            likes = None
                break
        # comments/shares live in raw["_object"] (added by 24.4 second call);
        # pre-24.4 rows do not have it, so they remain NULL.
        obj = raw.get("_object", {})
        comments = None
        shares = None
        if obj:
            summary = (obj.get("comments") or {}).get("summary", {})
            c = summary.get("total_count")
            if c is not None:
                try:
                    comments = int(c)
                except (TypeError, ValueError):
                    comments = None
            s = (obj.get("shares") or {}).get("count")
            if s is not None:
                try:
                    shares = int(s)
                except (TypeError, ValueError):
                    shares = None
        return likes, comments, shares

    if platform == "instagram":
        m: dict = {}
        for item in raw.get("data", []):
            name = item.get("name", "")
            values = item.get("values", [{}])
            val = values[0].get("value", 0) if values else 0
            m[name] = int(val) if val else 0
        likes = m["likes"] if "likes" in m else None
        comments = m["comments"] if "comments" in m else None
        shares = m["shares"] if "shares" in m else None
        return likes, comments, shares

    if platform == "threads":
        m = {}
        for item in raw.get("data", []):
            name = item.get("name", "")
            val = item.get("value", 0)
            m[name] = int(val) if val else 0
        likes = m["likes"] if "likes" in m else None
        comments = m["replies"] if "replies" in m else None
        shares = m["reposts"] if "reposts" in m else None
        return likes, comments, shares

    return None, None, None


def upgrade() -> None:
    op.add_column("post_metrics", sa.Column("likes", sa.BigInteger(), nullable=True))
    op.add_column("post_metrics", sa.Column("comments", sa.BigInteger(), nullable=True))
    op.add_column("post_metrics", sa.Column("shares", sa.BigInteger(), nullable=True))

    # One-time idempotent backfill: populate component columns from raw JSONB for
    # existing rows. Rows where likes is already set are skipped (idempotent).
    # Unavailability rows (no "data" key in raw) remain NULL — never fabricated.
    # Does not touch impressions or engagements.
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, platform, raw FROM post_metrics "
            "WHERE likes IS NULL AND raw IS NOT NULL"
        )
    ).fetchall()

    for row in rows:
        platform = row[1]
        raw = row[2] if isinstance(row[2], dict) else {}
        likes, comments, shares = _extract_components(platform, raw)
        if likes is None and comments is None and shares is None:
            continue
        conn.execute(
            sa.text(
                "UPDATE post_metrics "
                "SET likes = :likes, comments = :comments, shares = :shares "
                "WHERE id = :id"
            ),
            {"id": str(row[0]), "likes": likes, "comments": comments, "shares": shares},
        )


def downgrade() -> None:
    op.drop_column("post_metrics", "shares")
    op.drop_column("post_metrics", "comments")
    op.drop_column("post_metrics", "likes")
