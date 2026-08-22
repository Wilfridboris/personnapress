import uuid
from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, Enum as SAEnum, ForeignKey, Text, UniqueConstraint
from sqlalchemy import false as sa_false
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class RoadmapStatus(str, Enum):
    pending = "pending"
    generating = "generating"
    ready = "ready"
    approved = "approved"
    failed = "failed"


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Platform(str, Enum):
    wordpress = "wordpress"
    wordpress_com = "wordpress-com"
    webflow = "webflow"
    x = "x"
    linkedin = "linkedin"
    github_pages = "github_pages"
    instagram = "instagram"
    facebook_page = "facebook_page"
    threads = "threads"
    meta_pending = "meta_pending"


class CampaignStatus(str, Enum):
    pending_approval = "pending_approval"
    approved = "approved"
    published = "published"
    rejected = "rejected"
    failed = "failed"


class ArticleStatus(str, Enum):
    published = "published"
    hidden = "hidden"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: Optional[str] = None
    google_sub: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    github_installation_id: Optional[str] = Field(default=None, nullable=True)
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
    roadmaps_used: int = Field(default=0)
    deletion_scheduled_at: Optional[datetime] = Field(default=None, nullable=True)
    reengagement_email_sent_at: Optional[datetime] = Field(default=None, nullable=True)
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
    roadmap_config: Optional[dict] = Field(
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


class Roadmap(SQLModel, table=True):
    __tablename__ = "roadmaps"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    client_id: uuid.UUID = Field(foreign_key="clients.id")
    brain_dump: str = Field(sa_column=Column(Text, nullable=False))
    status: RoadmapStatus = Field(
        default=RoadmapStatus.pending,
        sa_column=Column(
            SAEnum(RoadmapStatus, name="roadmap_status_enum", create_constraint=True),
            nullable=False,
            default=RoadmapStatus.pending,
        ),
    )
    week_start_date: Optional[date] = Field(
        default=None, sa_column=Column(Date, nullable=True)
    )
    generate_images: bool = Field(default=True)
    skip_blog: bool = Field(default=False)
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
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
    instagram_caption: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    facebook_post: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    threads_post: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    image_url: Optional[str] = None
    image_alt: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    excerpt: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    meta_description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
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
    target_keyword: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    target_audience: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    secondary_keywords: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    campaign_type: str = Field(
        default="blog_full",
        sa_column=Column(Text, nullable=False, server_default="blog_full"),
    )
    skip_image: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default=sa_false()),
    )
    target_word_count: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    article_template: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    generation_mode: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    angle: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    github_pr_url: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True, index=True))
    roadmap_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("roadmaps.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    campaign_id: Optional[uuid.UUID] = Field(default=None, foreign_key="campaigns.id", index=True)
    client_id: Optional[uuid.UUID] = Field(default=None, foreign_key="clients.id", index=True)
    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", index=True)
    job_type: str
    status: str
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    attempt_count: int = Field(default=0)
    error_details: Optional[str] = None
    result: Optional[dict] = Field(default=None, sa_column=Column(JSONB, nullable=True))
    created_at: datetime = Field(default_factory=utcnow)


class GenerationLog(SQLModel, table=True):
    __tablename__ = "generation_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    campaign_id: uuid.UUID = Field(foreign_key="campaigns.id", index=True)
    gemini_tokens: Optional[int] = None
    replicate_count: Optional[int] = None
    created_at: datetime = Field(default_factory=utcnow)


class Article(SQLModel, table=True):
    __tablename__ = "articles"
    __table_args__ = (UniqueConstraint("client_id", "slug"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    client_id: uuid.UUID = Field(foreign_key="clients.id", index=True)
    campaign_id: Optional[uuid.UUID] = Field(default=None, foreign_key="campaigns.id", index=True, nullable=True)
    slug: str = Field(sa_column=Column(Text, nullable=False))
    title: str = Field(sa_column=Column(Text, nullable=False))
    html: str = Field(sa_column=Column(Text, nullable=False))
    excerpt: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    meta_description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    featured_image_url: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    featured_image_alt: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    author: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    tags: Optional[list] = Field(default=None, sa_column=Column(JSONB, nullable=True))
    category: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    status: ArticleStatus = Field(
        default=ArticleStatus.published,
        sa_column=Column(
            SAEnum(
                ArticleStatus,
                name="article_status_enum",
                create_constraint=True,
                values_callable=lambda obj: [e.value for e in obj],
            ),
            nullable=False,
            default=ArticleStatus.published,
        ),
    )
    reading_time_minutes: int = Field(default=1)
    published_at: datetime = Field(default_factory=utcnow)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class PublishedPost(SQLModel, table=True):
    __tablename__ = "published_posts"
    __table_args__ = (UniqueConstraint("campaign_id", "platform"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    campaign_id: uuid.UUID = Field(
        sa_column=Column(PGUUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False, index=True)
    )
    client_id: uuid.UUID = Field(
        sa_column=Column(PGUUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    )
    platform: str = Field(sa_column=Column(Text, nullable=False))
    platform_post_id: str = Field(sa_column=Column(Text, nullable=False))
    permalink: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    published_at: datetime = Field(sa_column=Column(DateTime(), nullable=False))
    created_at: datetime = Field(default_factory=utcnow)


class PostMetric(SQLModel, table=True):
    __tablename__ = "post_metrics"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    published_post_id: uuid.UUID = Field(
        sa_column=Column(PGUUID(as_uuid=True), ForeignKey("published_posts.id"), nullable=False)
    )
    client_id: uuid.UUID = Field(
        sa_column=Column(PGUUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    )
    platform: str = Field(sa_column=Column(Text, nullable=False))
    captured_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    impressions: Optional[int] = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    engagements: Optional[int] = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    likes: Optional[int] = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    comments: Optional[int] = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    shares: Optional[int] = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    raw: Optional[dict] = Field(default=None, sa_column=Column(JSONB, nullable=True))
    unavailable_reason: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )


class DeliveryToken(SQLModel, table=True):
    __tablename__ = "delivery_tokens"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    client_id: uuid.UUID = Field(foreign_key="clients.id", index=True)
    name: str = Field(sa_column=Column(Text, nullable=False))
    token_prefix: str = Field(sa_column=Column(Text, nullable=False, index=True))
    token_hash: str = Field(sa_column=Column(Text, nullable=False))
    revoked_at: Optional[datetime] = Field(default=None, nullable=True)
    last_used_at: Optional[datetime] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=utcnow)


class ArticleRevision(SQLModel, table=True):
    __tablename__ = "article_revisions"
    __table_args__ = (UniqueConstraint("article_id", "revision_number"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    article_id: uuid.UUID = Field(foreign_key="articles.id", index=True)
    revision_number: int
    title: str = Field(sa_column=Column(Text, nullable=False))
    html: str = Field(sa_column=Column(Text, nullable=False))
    excerpt: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    meta_description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    tags: Optional[list] = Field(default=None, sa_column=Column(JSONB, nullable=True))
    category: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    author: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    source: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=utcnow)
