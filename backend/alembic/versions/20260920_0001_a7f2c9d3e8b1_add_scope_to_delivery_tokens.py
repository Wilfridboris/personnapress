"""add_scope_to_delivery_tokens

Revision ID: a7f2c9d3e8b1
Revises: e5a6b7c8d9e0
Create Date: 2026-09-20

Story 12.7 -- adds a write-scope column to delivery_tokens so a token can be
minted as either read-only (ppd_) or write (ppw_). Existing rows are backfilled
to 'read'. No other schema changes.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7f2c9d3e8b1"
down_revision: Union[str, Sequence[str], None] = "e5a6b7c8d9e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "delivery_tokens",
        sa.Column("scope", sa.Text(), nullable=False, server_default="read"),
    )
    # Explicit backfill so any rows present before this migration are 'read'.
    op.execute("UPDATE delivery_tokens SET scope = 'read' WHERE scope IS NULL")


def downgrade() -> None:
    op.drop_column("delivery_tokens", "scope")
