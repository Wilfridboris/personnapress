import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class JobResponse(BaseModel):
    id: uuid.UUID
    campaign_id: Optional[uuid.UUID] = None
    client_id: Optional[uuid.UUID] = None
    job_type: str
    status: str
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    attempt_count: int
    error_details: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
