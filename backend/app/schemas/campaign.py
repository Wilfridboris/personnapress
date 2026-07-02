import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CampaignCreate(BaseModel):
    client_id: uuid.UUID
    brain_dump: str = Field(min_length=20, max_length=10000)

    @field_validator("brain_dump", mode="before")
    @classmethod
    def strip_brain_dump(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
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
    created_at: datetime
    updated_at: datetime


class CampaignCreateResponse(BaseModel):
    campaign_id: uuid.UUID
    job_id: uuid.UUID
