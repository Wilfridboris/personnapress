"""add_published_posts

Revision ID: c5d6e7f8a9b0
Revises: b7c2e9a4f318
Create Date: 2026-08-17 00:01:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = 'c5d6e7f8a9b0'
down_revision: Union[str, Sequence[str], None] = 'b7c2e9a4f318'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "published_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("platform", sa.Text(), nullable=False),
        sa.Column("platform_post_id", sa.Text(), nullable=False),
        sa.Column("permalink", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("campaign_id", "platform", name="published_posts_campaign_id_platform_key"),
    )
    op.create_index("ix_published_posts_campaign_id", "published_posts", ["campaign_id"])
    op.create_index("ix_published_posts_client_id", "published_posts", ["client_id"])


def downgrade() -> None:
    op.drop_index("ix_published_posts_client_id", "published_posts")
    op.drop_index("ix_published_posts_campaign_id", "published_posts")
    op.drop_table("published_posts")
