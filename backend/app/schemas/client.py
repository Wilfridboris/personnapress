import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl, field_validator


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


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    website_url: Optional[str] = None
    confirm_url_change: Optional[bool] = False

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

    model_config = {"from_attributes": True}


class ClientListItem(BaseModel):
    id: uuid.UUID
    name: str
    website_url: Optional[str] = None
    brand_voice_profile_status: str  # "ready" | "analyzing" | "incomplete"
    campaign_count: int = 0

    model_config = {"from_attributes": True}


class ClientListResponse(BaseModel):
    clients: list[ClientListItem]
    plan_at_limit: bool
    plan_tier: str
    client_limit: int
