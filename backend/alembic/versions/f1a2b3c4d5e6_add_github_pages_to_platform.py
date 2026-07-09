"""add_github_pages_to_platform_and_pr_url_to_campaigns

Revision ID: f1a2b3c4d5e6
Revises: e4582603a04a
Create Date: 2026-07-09

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e4582603a04a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block in PostgreSQL.
    with op.get_context().autocommit_block():
        op.execute(sa.text("ALTER TYPE platform_enum ADD VALUE IF NOT EXISTS 'github_pages'"))
    op.add_column("campaigns", sa.Column("github_pr_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("campaigns", "github_pr_url")
    # PostgreSQL does not support removing enum values — downgrade omits enum revert.
