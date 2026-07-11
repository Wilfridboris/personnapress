import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ClientCreate(BaseModel):
    name: str
    website_url: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Client name is required")
        if len(v) > 255:
            raise ValueError("Client name must be 255 characters or fewer")
        return v

    @field_validator("website_url")
    @classmethod
    def url_valid(cls, v: Optional[str]) -> Optional[str]:
        if not v or not v.strip():
            return None
        v = v.strip()
        try:
            HttpUrl(v)
        except Exception:
            raise ValueError("Invalid URL — must start with http:// or https://")
        return v


class ToneSliders(BaseModel):
    formal_casual: int = Field(ge=1, le=5)
    professional_friendly: int = Field(ge=1, le=5)
    concise_elaborate: int = Field(ge=1, le=5)


class QuestionnaireRequest(BaseModel):
    """Payload for POST /clients/{id}/questionnaire."""

    tone_sliders: ToneSliders
    sample_texts: List[str] = []  # 0–3 items (all optional)
    reference_urls: List[str] = []  # 0–3 items (optional)

    @field_validator("reference_urls")
    @classmethod
    def urls_valid(cls, v: List[str]) -> List[str]:
        for url in v:
            if url and url.strip():
                try:
                    HttpUrl(url.strip())
                except Exception:
                    raise ValueError(f"Invalid reference URL: {url}")
        return v


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    website_url: Optional[str] = None
    confirm_url_change: Optional[bool] = False
    brand_voice_profile: Optional[dict] = None  # Direct BVP overwrite (AC #3, Task 8)

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Client name is required")
        if len(v) > 255:
            raise ValueError("Client name must be 255 characters or fewer")
        return v

    @field_validator("website_url")
    @classmethod
    def url_valid(cls, v: Optional[str]) -> Optional[str]:
        if not v or not v.strip():
            return None
        v = v.strip()
        try:
            HttpUrl(v)
        except Exception:
            raise ValueError("Invalid URL — must start with http:// or https://")
        return v


class ClientResponse(BaseModel):
    id: uuid.UUID
    name: str
    website_url: Optional[str] = None
    brand_voice_profile: Optional[dict] = None
    job_id: Optional[uuid.UUID] = None
    campaign_count: int = 0
    created_at: datetime
    # Voice-setup state helpers (populated by router, not ORM)
    ingestion_failed: bool = False     # True when Gemini extraction failed (AC4)
    ingestion_no_content: bool = False  # True when no scrapeable content found (AC5)
    ingestion_error: Optional[str] = None

    model_config = {"from_attributes": True}


class ClientListItem(BaseModel):
    id: uuid.UUID
    name: str
    website_url: Optional[str] = None
    brand_voice_profile_status: str  # "ready" | "analyzing" | "incomplete"
    brand_voice_profile: Optional[dict] = None
    campaign_count: int = 0

    model_config = {"from_attributes": True}


class ClientListResponse(BaseModel):
    clients: list[ClientListItem]
    plan_at_limit: bool
    plan_tier: str
    client_limit: int
