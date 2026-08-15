"""add_platform_native_social_fields_to_campaigns

Revision ID: ecd78b43ce50
Revises: ae296c4a3414
Create Date: 2026-08-14 21:31:35.661921

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ecd78b43ce50'
down_revision: Union[str, Sequence[str], None] = 'ae296c4a3414'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("instagram_caption", sa.Text(), nullable=True))
    op.add_column("campaigns", sa.Column("facebook_post", sa.Text(), nullable=True))
    op.add_column("campaigns", sa.Column("threads_post", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("campaigns", "threads_post")
    op.drop_column("campaigns", "facebook_post")
    op.drop_column("campaigns", "instagram_caption")
