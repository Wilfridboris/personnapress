"""add_reengagement_email_sent_at_to_subscriptions

Revision ID: d7c9202f2367
Revises: d1e2f3a4b5c6
Create Date: 2026-07-26 19:03:05.635665

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd7c9202f2367'
down_revision: Union[str, Sequence[str], None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('subscriptions', sa.Column('reengagement_email_sent_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('subscriptions', 'reengagement_email_sent_at')
