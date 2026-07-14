"""add_articles_and_revisions

Revision ID: cc76abfc05a1
Revises: f1a2b3c4d5e6
Create Date: 2026-07-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "cc76abfc05a1"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id"), nullable=True),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("html", sa.Text(), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("meta_description", sa.Text(), nullable=True),
        sa.Column("featured_image_url", sa.Text(), nullable=True),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.JSONB(), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("published", "hidden", name="article_status_enum", create_constraint=True),
            nullable=False,
            server_default="published",
        ),
        sa.Column("reading_time_minutes", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("published_at", sa.TIMESTAMP(timezone=False), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=False), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=False), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("client_id", "slug", name="uq_articles_client_slug"),
    )
    op.create_index("ix_articles_client_id", "articles", ["client_id"])
    op.create_index("ix_articles_campaign_id", "articles", ["campaign_id"])

    op.create_table(
        "article_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("article_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("articles.id"), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("html", sa.Text(), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("meta_description", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.JSONB(), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=False), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("article_id", "revision_number", name="uq_article_revisions_article_num"),
        sa.CheckConstraint("source IN ('initial', 'edit', 'restore')", name="ck_article_revisions_source"),
    )
    op.create_index("ix_article_revisions_article_id", "article_revisions", ["article_id"])


def downgrade() -> None:
    op.drop_table("article_revisions")
    op.drop_table("articles")
    op.execute(sa.text("DROP TYPE IF EXISTS article_status_enum"))
