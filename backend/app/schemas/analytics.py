import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class SeriesPoint(BaseModel):
    captured_at: datetime
    impressions: Optional[int]
    engagements: Optional[int]


class BestPost(BaseModel):
    published_post_id: uuid.UUID
    platform: Literal["facebook_page", "instagram", "threads"]
    campaign_title: str
    engagements: Optional[int]
    permalink: Optional[str]


class ClientSummaryResponse(BaseModel):
    client_id: uuid.UUID
    total_impressions: Optional[int]
    total_engagements: Optional[int]
    total_likes: Optional[int]
    total_comments: Optional[int]
    total_shares: Optional[int]
    engagement_rate: Optional[float]
    posts_tracked: int
    best_post: Optional[BestPost]
    freshest_captured_at: Optional[datetime]


class PostMetricItem(BaseModel):
    published_post_id: uuid.UUID
    platform: Literal["facebook_page", "instagram", "threads"]
    campaign_title: str
    campaign_excerpt: Optional[str]
    latest_impressions: Optional[int]
    latest_engagements: Optional[int]
    latest_likes: Optional[int]
    latest_comments: Optional[int]
    latest_shares: Optional[int]
    engagement_rate: Optional[float]
    permalink: Optional[str]
    captured_at: Optional[datetime]
    series: list[SeriesPoint]
    unavailable_reason: Optional[str]


class ClientPostMetricsResponse(BaseModel):
    client_id: uuid.UUID
    items: list[PostMetricItem]
    freshest_captured_at: Optional[datetime]
