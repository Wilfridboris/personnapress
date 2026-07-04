"""add_wordpress_com_to_platform_enum

Revision ID: a1b2c3d4e5f6
Revises: c3d8f2a91b7e
Create Date: 2026-07-03 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'd4e9f1a02b3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block in PostgreSQL.
    with op.get_context().autocommit_block():
        op.execute(sa.text("ALTER TYPE platform_enum ADD VALUE IF NOT EXISTS 'wordpress-com'"))


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without dropping and recreating the type.
    # A full downgrade would require migrating existing rows and recreating the enum — omitted as irreversible.
    pass
