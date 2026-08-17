"""add_post_metrics

Revision ID: 444913f949d4
Revises: c5d6e7f8a9b0
Create Date: 2026-08-17 13:55:28.968799

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '444913f949d4'
down_revision: Union[str, Sequence[str], None] = 'c5d6e7f8a9b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "post_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column("published_post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("published_posts.id"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("platform", sa.Text(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("impressions", sa.BigInteger(), nullable=True),
        sa.Column("engagements", sa.BigInteger(), nullable=True),
        sa.Column("raw", postgresql.JSONB(), nullable=True),
        sa.Column("unavailable_reason", sa.Text(), nullable=True),
    )
    # Composite index supports "latest snapshot per post" DISTINCT ON / window queries
    op.execute(
        "CREATE INDEX ix_post_metrics_post_captured "
        "ON post_metrics (published_post_id ASC, captured_at DESC)"
    )
    op.create_index("ix_post_metrics_client_id", "post_metrics", ["client_id"])


def downgrade() -> None:
    op.drop_index("ix_post_metrics_client_id", table_name="post_metrics")
    op.execute("DROP INDEX IF EXISTS ix_post_metrics_post_captured")
    op.drop_table("post_metrics")
