"""add_generation_mode_to_campaigns

Revision ID: 4bfe6734e20c
Revises: 444913f949d4
Create Date: 2026-08-18 19:14:46.957170

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4bfe6734e20c'
down_revision: Union[str, Sequence[str], None] = '444913f949d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('campaigns', sa.Column('generation_mode', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('campaigns', 'generation_mode')
