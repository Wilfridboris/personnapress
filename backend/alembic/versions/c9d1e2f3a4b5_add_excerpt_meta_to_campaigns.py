"""add excerpt and meta_description to campaigns

Revision ID: c9d1e2f3a4b5
Revises: bfba3f0b70ff
Create Date: 2026-07-24

"""
from alembic import op
import sqlalchemy as sa

revision = "c9d1e2f3a4b5"
down_revision = "bfba3f0b70ff"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("excerpt", sa.Text(), nullable=True))
    op.add_column("campaigns", sa.Column("meta_description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("campaigns", "meta_description")
    op.drop_column("campaigns", "excerpt")
