from datetime import datetime

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
    plan_limits: PlanLimits
