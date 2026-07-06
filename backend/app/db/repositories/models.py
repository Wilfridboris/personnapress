import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import Column, Enum as SAEnum, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Platform(str, Enum):
    wordpress = "wordpress"
    wordpress_com = "wordpress-com"
    webflow = "webflow"
    x = "x"
    linkedin = "linkedin"


class CampaignStatus(str, Enum):
    pending_approval = "pending_approval"
    approved = "approved"
    published = "published"
    rejected = "rejected"
    failed = "failed"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: Optional[str] = None
    google_sub: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    verified: bool = Field(default=False)
    onboarding_completed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utcnow)


class Subscription(SQLModel, table=True):
    __tablename__ = "subscriptions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    stripe_sub_id: Optional[str] = None
    plan_tier: str
    status: str
    campaigns_used: int = Field(default=0)
    clients_count: int = Field(default=0)
    image_gen_used: int = Field(default=0)
    billing_cycle_start: datetime
    billing_cycle_end: datetime
    deletion_scheduled_at: Optional[datetime] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Client(SQLModel, table=True):
    __tablename__ = "clients"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    name: str
    website_url: Optional[str] = None
    brand_voice_profile: Optional[dict] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class PlatformConnection(SQLModel, table=True):
    __tablename__ = "platform_connections"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    client_id: uuid.UUID = Field(foreign_key="clients.id", index=True)
    platform: str = Field(
        sa_column=Column(
            SAEnum(
                Platform,
                name="platform_enum",
                create_constraint=True,
                # Python 3.11+ changed str(StrEnum.member) to return the member name.
                # Explicitly use .value so PostgreSQL always gets "wordpress-com" not "wordpress_com".
                values_callable=lambda obj: [e.value for e in obj],
            ),
            nullable=False,
        )
    )
    encrypted_credentials: str
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Campaign(SQLModel, table=True):
    __tablename__ = "campaigns"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    client_id: uuid.UUID = Field(foreign_key="clients.id", index=True)
    brain_dump: str
    blog_html: Optional[str] = None
    x_post: Optional[str] = None
    linkedin_post: Optional[str] = None
    image_url: Optional[str] = None
    status: str = Field(
        default=CampaignStatus.pending_approval,
        sa_column=Column(
            SAEnum(CampaignStatus, name="campaign_status_enum", create_constraint=True),
            nullable=False,
            default=CampaignStatus.pending_approval,
        ),
    )
    voice_score: Optional[dict] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    rejection_reason: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    image_regen_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    campaign_id: Optional[uuid.UUID] = Field(default=None, foreign_key="campaigns.id", index=True)
    client_id: Optional[uuid.UUID] = Field(default=None, foreign_key="clients.id", index=True)
    job_type: str
    status: str
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    attempt_count: int = Field(default=0)
    error_details: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)


class GenerationLog(SQLModel, table=True):
    __tablename__ = "generation_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    campaign_id: uuid.UUID = Field(foreign_key="campaigns.id", index=True)
    gemini_tokens: Optional[int] = None
    replicate_count: Optional[int] = None
    created_at: datetime = Field(default_factory=utcnow)
