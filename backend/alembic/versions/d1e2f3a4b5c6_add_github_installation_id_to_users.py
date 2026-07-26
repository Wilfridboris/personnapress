"""add github_installation_id to users

Revision ID: d1e2f3a4b5c6
Revises: c9d1e2f3a4b5
Create Date: 2026-07-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "c9d1e2f3a4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("github_installation_id", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "github_installation_id")
