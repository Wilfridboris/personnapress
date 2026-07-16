from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, field_validator


class PublishRequest(BaseModel):
    platforms: Optional[list[str]] = None  # None = publish all connected platforms


class PublishHeadlessRequest(BaseModel):
    scheduled_at: Optional[datetime] = None  # None = publish immediately

    @field_validator("scheduled_at")
    @classmethod
    def must_be_timezone_aware(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None and v.tzinfo is None:
            raise ValueError("scheduled_at must include timezone information")
        return v
