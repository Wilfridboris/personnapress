"""add_user_id_to_jobs

Revision ID: b7c2e9a4f318
Revises: 5da92c280d07
Create Date: 2026-08-15 23:32:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = 'b7c2e9a4f318'
down_revision: Union[str, Sequence[str], None] = '5da92c280d07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_jobs_user_id", "jobs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_jobs_user_id", "jobs")
    op.drop_column("jobs", "user_id")
