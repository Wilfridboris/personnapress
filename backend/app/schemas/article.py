import re
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.html_sanitize import is_allowed_image_src

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ArticlePatch(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    html: Optional[str] = Field(None, max_length=500_000)
    excerpt: Optional[str] = Field(None, max_length=1_000)
    meta_description: Optional[str] = Field(None, max_length=500)
    tags: Optional[list[str]] = None
    category: Optional[str] = Field(None, max_length=200)
    author: Optional[str] = Field(None, max_length=200)
    slug: Optional[str] = Field(None, max_length=60)
    status: Optional[str] = Field(None)
    featured_image_url: Optional[str] = Field(None, max_length=1000)
    featured_image_alt: Optional[str] = Field(None, max_length=500)

    @field_validator("title", "excerpt", "meta_description", "category", "author", "featured_image_alt", mode="before")
    @classmethod
    def strip_text(cls, v: object) -> object:
        if isinstance(v, str):
            stripped = v.strip()
            return stripped if stripped else None
        return v

    @field_validator("slug", mode="before")
    @classmethod
    def strip_slug(cls, v: object) -> object:
        if isinstance(v, str):
            stripped = v.strip()
            return stripped if stripped else None
        return v

    @field_validator("slug", mode="after")
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not _SLUG_RE.match(v):
            raise ValueError(
                "Slug must contain only lowercase letters, digits, and hyphens "
                "(no leading/trailing hyphens, no consecutive hyphens)."
            )
        return v

    @field_validator("status", mode="after")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("published", "hidden"):
            raise ValueError("status must be 'published' or 'hidden'.")
        return v

    @field_validator("featured_image_url", mode="after")
    @classmethod
    def validate_featured_image_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not is_allowed_image_src(v):
            raise ValueError("featured_image_url must be a URL from this application's storage.")
        return v


class ArticleListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    status: str
    published_at: datetime
    updated_at: datetime


class ArticleListResponse(BaseModel):
    items: list[ArticleListItem]
    total: int


class ArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    campaign_id: Optional[uuid.UUID]
    slug: str
    title: str
    html: str
    excerpt: Optional[str]
    meta_description: Optional[str]
    featured_image_url: Optional[str]
    featured_image_alt: Optional[str]
    author: Optional[str]
    tags: Optional[list]
    category: Optional[str]
    status: str
    reading_time_minutes: int
    published_at: datetime
    created_at: datetime
    updated_at: datetime


class RevisionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    revision_number: int
    source: str
    created_at: datetime


class RevisionListResponse(BaseModel):
    items: list[RevisionListItem]


class RevisionDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    revision_number: int
    title: str
    html: str
    excerpt: Optional[str]
    meta_description: Optional[str]
    tags: Optional[list]
    category: Optional[str]
    author: Optional[str]
    source: str
    created_at: datetime


class PublishHeadlessResponse(BaseModel):
    article_id: uuid.UUID
    slug: str
    status: str
