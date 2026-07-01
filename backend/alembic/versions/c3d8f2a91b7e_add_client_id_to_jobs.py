"""add_client_id_to_jobs

Revision ID: c3d8f2a91b7e
Revises: 2a7f3c8d1e04
Create Date: 2026-07-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = 'c3d8f2a91b7e'
down_revision: Union[str, Sequence[str], None] = '2a7f3c8d1e04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_jobs_client_id", "jobs", ["client_id"])


def downgrade() -> None:
    op.drop_index("ix_jobs_client_id", "jobs")
    op.drop_column("jobs", "client_id")
