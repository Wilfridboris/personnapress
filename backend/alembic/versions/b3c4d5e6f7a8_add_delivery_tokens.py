"""add_delivery_tokens

Revision ID: b3c4d5e6f7a8
Revises: cc76abfc05a1
Create Date: 2026-07-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "cc76abfc05a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "delivery_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("token_prefix", sa.Text(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=False), nullable=True),
        sa.Column("last_used_at", sa.TIMESTAMP(timezone=False), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=False), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_delivery_tokens_client_id", "delivery_tokens", ["client_id"])
    op.create_index("ix_delivery_tokens_token_prefix", "delivery_tokens", ["token_prefix"])


def downgrade() -> None:
    op.drop_table("delivery_tokens")
