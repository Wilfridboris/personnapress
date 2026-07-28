"""add_approved_to_roadmap_status

Revision ID: 978fa9606dc3
Revises: 471dca414d29
Create Date: 2026-07-27 19:30:05.781741

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '978fa9606dc3'
down_revision: Union[str, Sequence[str], None] = '471dca414d29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(sa.text("ALTER TYPE roadmap_status_enum ADD VALUE IF NOT EXISTS 'approved'"))


def downgrade() -> None:
    pass  # PostgreSQL does not support removing enum values
