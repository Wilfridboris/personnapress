"""add_campaign_type

Revision ID: 2e17c8e43612
Revises: a4b5c6d7e8f9
Create Date: 2026-08-01 00:46:03.548800

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e17c8e43612'
down_revision: Union[str, Sequence[str], None] = 'a4b5c6d7e8f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "campaigns",
        sa.Column("campaign_type", sa.Text(), nullable=True),
    )
    op.execute("UPDATE campaigns SET campaign_type = 'blog_full' WHERE campaign_type IS NULL")
    op.alter_column("campaigns", "campaign_type", nullable=False, server_default="blog_full")


def downgrade() -> None:
    op.drop_column("campaigns", "campaign_type")
