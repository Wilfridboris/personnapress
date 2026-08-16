"""add_result_to_jobs

Revision ID: 5da92c280d07
Revises: ecd78b43ce50
Create Date: 2026-08-15 23:09:58.378344

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5da92c280d07'
down_revision: Union[str, Sequence[str], None] = 'ecd78b43ce50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('jobs', sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('jobs', 'result')
