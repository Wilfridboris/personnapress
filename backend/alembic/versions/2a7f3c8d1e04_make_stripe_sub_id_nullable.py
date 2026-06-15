"""make_stripe_sub_id_nullable

Revision ID: 2a7f3c8d1e04
Revises: 9e1e7111a5e5
Create Date: 2026-06-15 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '2a7f3c8d1e04'
down_revision: Union[str, Sequence[str], None] = '9e1e7111a5e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("subscriptions", "stripe_sub_id", nullable=True, existing_type=sa.String())


def downgrade() -> None:
    op.alter_column("subscriptions", "stripe_sub_id", nullable=False, existing_type=sa.String())
