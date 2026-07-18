import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PublishJobInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    attempt_count: int
    error_details: Optional[str]
    status: str


_BLOG_HTML_MAX = 200_000
_SOCIAL_POST_MAX = 5_000


class CampaignPatch(BaseModel):
    blog_html: Optional[str] = Field(None, max_length=_BLOG_HTML_MAX)
    x_post: Optional[str] = Field(None, max_length=_SOCIAL_POST_MAX)
    linkedin_post: Optional[str] = Field(None, max_length=_SOCIAL_POST_MAX)


class CampaignCreate(BaseModel):
    client_id: uuid.UUID
    brain_dump: str = Field(min_length=20, max_length=10000)
    target_keyword: Optional[str] = Field(default=None, max_length=200)
    target_audience: Optional[str] = Field(default=None, max_length=500)
    secondary_keywords: Optional[str] = Field(default=None, max_length=500)

    @field_validator("brain_dump", mode="before")
    @classmethod
    def strip_brain_dump(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @field_validator("target_keyword", "target_audience", "secondary_keywords", mode="before")
    @classmethod
    def strip_optional_text(cls, v: object) -> object:
        if isinstance(v, str):
            stripped = v.strip()
            return stripped if stripped else None
        return v


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    client_name: Optional[str] = None
    brain_dump: str
    blog_html: Optional[str]
    x_post: Optional[str]
    linkedin_post: Optional[str]
    image_url: Optional[str]
    status: str
    voice_score: Optional[dict]
    rejection_reason: Optional[str]
    scheduled_at: Optional[datetime]
    image_regen_count: int
    github_pr_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CampaignDetailResponse(CampaignResponse):
    publish_job: Optional[PublishJobInfo] = None
    article_id: Optional[uuid.UUID] = None
    article_slug: Optional[str] = None


class CampaignListResponse(BaseModel):
    items: list[CampaignResponse]
    total: int


class CampaignCreateResponse(BaseModel):
    campaign_id: uuid.UUID
    job_id: uuid.UUID
