"""add image_alt to campaigns

Revision ID: bfba3f0b70ff
Revises: a3b4c5d6e7f8
Create Date: 2026-07-21

"""
from alembic import op
import sqlalchemy as sa

revision = "bfba3f0b70ff"
down_revision = "a3b4c5d6e7f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("image_alt", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("campaigns", "image_alt")
