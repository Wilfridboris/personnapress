"""add_onboarding_step_to_users

Revision ID: e5a6b7c8d9e0
Revises: 5c08a8909153
Create Date: 2026-09-08 00:01:00.000000

Story 26.5 -- adds nullable integer onboarding_step to users table so
each completed onboarding step can be persisted for resume-on-return.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5a6b7c8d9e0"
down_revision: Union[str, Sequence[str], None] = "5c08a8909153"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("onboarding_step", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "onboarding_step")
