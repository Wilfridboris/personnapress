"""add_meta_pending_platform

Revision ID: b89b98f2591f
Revises: 4a5b6c7d8e9f
Create Date: 2026-08-01 11:03:10.889053

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b89b98f2591f'
down_revision: Union[str, Sequence[str], None] = '4a5b6c7d8e9f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(sa.text("ALTER TYPE platform_enum ADD VALUE IF NOT EXISTS 'meta_pending'"))


def downgrade() -> None:
    # PostgreSQL does not support removing enum values -- downgrade omits enum revert.
    pass
