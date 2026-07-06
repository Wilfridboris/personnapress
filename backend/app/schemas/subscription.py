from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PlanLimits(BaseModel):
    clients: int
    campaigns: int
    image_gens: int


class SubscriptionResponse(BaseModel):
    plan_tier: str
    status: str
    campaigns_used: int
    clients_count: int
    image_gen_used: int
    billing_cycle_start: datetime
    billing_cycle_end: datetime
    deletion_scheduled_at: Optional[datetime] = None
    plan_limits: PlanLimits
