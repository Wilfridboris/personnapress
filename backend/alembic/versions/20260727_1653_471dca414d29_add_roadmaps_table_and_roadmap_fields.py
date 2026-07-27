"""add_roadmaps_table_and_roadmap_fields

Revision ID: 471dca414d29
Revises: d7c9202f2367
Create Date: 2026-07-27 16:53:43.873541

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '471dca414d29'
down_revision: Union[str, Sequence[str], None] = 'd7c9202f2367'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'roadmaps',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('client_id', sa.Uuid(), nullable=False),
        sa.Column('brain_dump', sa.Text(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('pending', 'generating', 'ready', 'failed', name='roadmap_status_enum', create_constraint=True),
            nullable=False,
            server_default='pending',
        ),
        sa.Column('week_start_date', sa.Date(), nullable=True),
        sa.Column('generate_images', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('skip_blog', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_roadmaps_user_id'), 'roadmaps', ['user_id'], unique=False)

    op.add_column('campaigns', sa.Column('roadmap_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f('ix_campaigns_roadmap_id'), 'campaigns', ['roadmap_id'], unique=False)
    op.create_foreign_key(
        'fk_campaigns_roadmap_id_roadmaps',
        'campaigns', 'roadmaps',
        ['roadmap_id'], ['id'],
        ondelete='SET NULL',
    )

    op.add_column('clients', sa.Column('roadmap_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    op.add_column(
        'subscriptions',
        sa.Column('roadmaps_used', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('subscriptions', 'roadmaps_used')
    op.drop_column('clients', 'roadmap_config')
    op.drop_constraint('fk_campaigns_roadmap_id_roadmaps', 'campaigns', type_='foreignkey')
    op.drop_index(op.f('ix_campaigns_roadmap_id'), table_name='campaigns')
    op.drop_column('campaigns', 'roadmap_id')
    op.drop_index(op.f('ix_roadmaps_user_id'), table_name='roadmaps')
    op.drop_table('roadmaps')
    op.execute("DROP TYPE IF EXISTS roadmap_status_enum")
