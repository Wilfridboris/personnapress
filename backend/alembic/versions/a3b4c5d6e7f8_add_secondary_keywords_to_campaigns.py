"""add_secondary_keywords_to_campaigns

Revision ID: a3b4c5d6e7f8
Revises: d7e8f9a0b1c2
Create Date: 2026-07-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, Sequence[str], None] = "d7e8f9a0b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("secondary_keywords", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("campaigns", "secondary_keywords")
