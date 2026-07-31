"""add_meta_platforms

Revision ID: a4b5c6d7e8f9
Revises: 978fa9606dc3
Create Date: 2026-07-31 00:01:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a4b5c6d7e8f9'
down_revision: Union[str, Sequence[str], None] = '978fa9606dc3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block in PostgreSQL.
    with op.get_context().autocommit_block():
        op.execute(sa.text("ALTER TYPE platform_enum ADD VALUE IF NOT EXISTS 'instagram'"))
        op.execute(sa.text("ALTER TYPE platform_enum ADD VALUE IF NOT EXISTS 'facebook_page'"))
        op.execute(sa.text("ALTER TYPE platform_enum ADD VALUE IF NOT EXISTS 'threads'"))


def downgrade() -> None:
    raise NotImplementedError(
        "ALTER TYPE ADD VALUE cannot be reversed without dropping and recreating the enum type. "
        "Manual downgrade required: migrate existing rows away from instagram/facebook_page/threads "
        "before dropping and recreating platform_enum."
    )
