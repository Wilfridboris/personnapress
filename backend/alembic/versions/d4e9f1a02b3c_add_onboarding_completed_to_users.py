"""add_onboarding_completed_to_users

Revision ID: d4e9f1a02b3c
Revises: c3d8f2a91b7e
Create Date: 2026-07-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e9f1a02b3c"
down_revision: Union[str, Sequence[str], None] = "c3d8f2a91b7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "onboarding_completed",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "onboarding_completed")
