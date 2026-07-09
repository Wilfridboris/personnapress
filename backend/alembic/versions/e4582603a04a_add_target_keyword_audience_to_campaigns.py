"""add_target_keyword_audience_to_campaigns

Revision ID: e4582603a04a
Revises: e5f6a7b8c9d0
Create Date: 2026-07-09

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e4582603a04a"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("target_keyword", sa.Text(), nullable=True))
    op.add_column("campaigns", sa.Column("target_audience", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("campaigns", "target_audience")
    op.drop_column("campaigns", "target_keyword")
