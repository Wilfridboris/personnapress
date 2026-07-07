"""add deletion_scheduled_at to subscriptions

Revision ID: e5f6a7b8c9d0
Revises: d4e9f1a02b3c
Create Date: 2026-07-04

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("deletion_scheduled_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "deletion_scheduled_at")
