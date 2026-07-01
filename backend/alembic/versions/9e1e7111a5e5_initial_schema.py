"""initial_schema

Revision ID: 9e1e7111a5e5
Revises:
Create Date: 2026-06-14 23:54:08.616559

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = '9e1e7111a5e5'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(), nullable=True),
        sa.Column("google_sub", sa.String(), nullable=True),
        sa.Column("stripe_customer_id", sa.String(), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("stripe_sub_id", sa.String(), nullable=False),
        sa.Column("plan_tier", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("campaigns_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clients_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("image_gen_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("billing_cycle_start", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("billing_cycle_end", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])

    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("website_url", sa.String(), nullable=True),
        sa.Column("brand_voice_profile", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_clients_user_id", "clients", ["user_id"])

    # Create enum type first, then reuse the same object in create_table.
    # Using create_type=False on the object means _on_table_create won't
    # attempt a second CREATE TYPE. checkfirst=True on .create() handles
    # idempotency (no-ops if the type already exists).
    platform_enum = postgresql.ENUM(
        "wordpress", "webflow", "x", "linkedin",
        name="platform_enum",
        create_type=False,
    )
    platform_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "platform_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("platform", platform_enum, nullable=False),
        sa.Column("encrypted_credentials", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_platform_connections_client_id", "platform_connections", ["client_id"])

    campaign_status_enum = postgresql.ENUM(
        "pending_approval", "approved", "published", "rejected", "failed",
        name="campaign_status_enum",
        create_type=False,
    )
    campaign_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("brain_dump", sa.Text(), nullable=False),
        sa.Column("blog_html", sa.Text(), nullable=True),
        sa.Column("x_post", sa.Text(), nullable=True),
        sa.Column("linkedin_post", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column(
            "status",
            campaign_status_enum,
            nullable=False,
            server_default="pending_approval",
        ),
        sa.Column("voice_score", postgresql.JSONB(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("scheduled_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("image_regen_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_campaigns_client_id", "campaigns", ["client_id"])

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id"), nullable=True),
        sa.Column("job_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("scheduled_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_jobs_campaign_id", "jobs", ["campaign_id"])

    op.create_table(
        "generation_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("gemini_tokens", sa.Integer(), nullable=True),
        sa.Column("replicate_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_generation_logs_user_id", "generation_logs", ["user_id"])
    op.create_index("ix_generation_logs_campaign_id", "generation_logs", ["campaign_id"])


def downgrade() -> None:
    op.drop_index("ix_generation_logs_campaign_id", "generation_logs")
    op.drop_index("ix_generation_logs_user_id", "generation_logs")
    op.drop_table("generation_logs")
    op.drop_index("ix_jobs_campaign_id", "jobs")
    op.drop_table("jobs")
    op.drop_table("campaigns")
    op.drop_index("ix_platform_connections_client_id", "platform_connections")
    op.drop_table("platform_connections")
    op.drop_index("ix_clients_user_id", "clients")
    op.drop_table("clients")
    op.drop_index("ix_subscriptions_user_id", "subscriptions")
    op.drop_table("subscriptions")
    op.drop_index("ix_users_email", "users")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS campaign_status_enum")
    op.execute("DROP TYPE IF EXISTS platform_enum")
