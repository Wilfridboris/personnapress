"""add_featured_image_alt_to_articles

Revision ID: d7e8f9a0b1c2
Revises: cc76abfc05a1
Create Date: 2026-07-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d7e8f9a0b1c2"
down_revision: Union[str, Sequence[str], None] = "cc76abfc05a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("featured_image_alt", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("articles", "featured_image_alt")
