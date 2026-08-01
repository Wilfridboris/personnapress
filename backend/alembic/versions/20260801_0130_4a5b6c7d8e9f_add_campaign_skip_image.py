"""add_campaign_skip_image

Revision ID: 4a5b6c7d8e9f
Revises: 2e17c8e43612
Create Date: 2026-08-01 01:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a5b6c7d8e9f'
down_revision: Union[str, Sequence[str], None] = '2e17c8e43612'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "campaigns",
        sa.Column("skip_image", sa.Boolean(), nullable=True),
    )
    op.execute("UPDATE campaigns SET skip_image = false WHERE skip_image IS NULL")
    op.alter_column("campaigns", "skip_image", nullable=False, server_default=sa.false())


def downgrade() -> None:
    op.drop_column("campaigns", "skip_image")
