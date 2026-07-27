"""Roadmap API endpoints (Epic 20).

POST /api/v1/roadmaps      — create roadmap and kick off generation
GET  /api/v1/roadmaps/{id} — poll status and list child campaigns
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.dependencies import get_current_user
from app.db.connection import get_session
from app.db.repositories.clients import get_client
from app.db.repositories.models import Campaign, Roadmap, RoadmapStatus
from app.services.roadmap import generate_roadmap
from app.services.subscription_service import check_roadmap_limit, check_trial_not_expired

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])

_INVALID_SESSION = {"error": {"code": "INVALID_SESSION", "message": "Invalid session.", "detail": {}}}
_NOT_FOUND = {"error": {"code": "ROADMAP_NOT_FOUND", "message": "Roadmap not found.", "detail": {}}}
_FORBIDDEN = {"error": {"code": "FORBIDDEN", "message": "Access denied.", "detail": {}}}


def _next_monday(ref: date) -> date:
    """Return the next Monday on or after ref."""
    days_ahead = (0 - ref.weekday()) % 7
    return ref + timedelta(days=days_ahead)


class RoadmapCreateRequest(BaseModel):
    brain_dump: str = Field(min_length=20, max_length=10000)
    client_id: uuid.UUID
    linkedin_count: int = Field(default=0, ge=0, le=14)
    twitter_count: int = Field(default=0, ge=0, le=14)
    blog_enabled: bool = True
    generate_images: bool = True
    week_start_date: Optional[date] = None

    @model_validator(mode="after")
    def at_least_one_post(self) -> "RoadmapCreateRequest":
        total = self.linkedin_count + self.twitter_count + (1 if self.blog_enabled else 0)
        if total == 0:
            raise ValueError("At least one post type must be enabled (blog, LinkedIn, or X).")
        return self


class RoadmapCreateResponse(BaseModel):
    roadmap_id: uuid.UUID
    job_id: str


class CampaignSummary(BaseModel):
    id: uuid.UUID
    campaign_type: str
    platform_hint: str
    x_post: Optional[str] = None
    linkedin_post: Optional[str] = None
    blog_title: Optional[str] = None
    image_url: Optional[str] = None
    status: str
    scheduled_for: Optional[datetime] = None


class RoadmapStatusResponse(BaseModel):
    id: uuid.UUID
    status: str
    error_message: Optional[str] = None
    generate_images: bool
    skip_blog: bool
    week_start_date: Optional[date] = None
    campaigns: list[CampaignSummary]


def _platform_hint(campaign: Campaign) -> str:
    if campaign.blog_html is not None:
        return "blog_full"
    if campaign.linkedin_post is not None:
        return "linkedin"
    return "x"


def _blog_title(campaign: Campaign) -> Optional[str]:
    if not campaign.blog_html:
        return None
    import re
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", campaign.blog_html, re.IGNORECASE | re.DOTALL)
    if not h1:
        return None
    return re.sub(r"<[^>]+>", "", h1.group(1)).strip() or None


async def _run_roadmap_generation(roadmap_id: uuid.UUID) -> None:
    """Background task: owns its own DB session."""
    from app.db.connection import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await generate_roadmap(roadmap_id, db)


@router.post("", status_code=202, response_model=RoadmapCreateResponse)
async def create_roadmap(
    body: RoadmapCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> RoadmapCreateResponse:
    try:
        user_id = uuid.UUID(current_user["user_id"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail=_INVALID_SESSION)

    client = await get_client(db, body.client_id)
    if not client or client.user_id != user_id:
        raise HTTPException(status_code=404, detail={"error": {"code": "CLIENT_NOT_FOUND", "message": "Client not found.", "detail": {}}})

    await check_trial_not_expired(user_id, db, "create roadmaps")
    await check_roadmap_limit(db, user_id)

    # Upsert roadmap_config on the client
    client.roadmap_config = {
        "linkedin_count": body.linkedin_count,
        "twitter_count": body.twitter_count,
        "blog_enabled": body.blog_enabled,
        "images_enabled": body.generate_images,
    }
    client.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    ref_date = body.week_start_date or datetime.now(timezone.utc).date()
    week_start = _next_monday(ref_date)

    roadmap = Roadmap(
        user_id=user_id,
        client_id=body.client_id,
        brain_dump=body.brain_dump,
        status=RoadmapStatus.pending,
        week_start_date=week_start,
        generate_images=body.generate_images,
        skip_blog=not body.blog_enabled,
    )
    db.add(roadmap)
    await db.flush()
    await db.refresh(roadmap)
    await db.commit()

    background_tasks.add_task(_run_roadmap_generation, roadmap.id)

    return RoadmapCreateResponse(roadmap_id=roadmap.id, job_id=str(roadmap.id))


@router.get("/{roadmap_id}", response_model=RoadmapStatusResponse)
async def get_roadmap_status(
    roadmap_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> RoadmapStatusResponse:
    try:
        user_id = uuid.UUID(current_user["user_id"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail=_INVALID_SESSION)

    result = await db.execute(select(Roadmap).where(Roadmap.id == roadmap_id))
    roadmap = result.scalar_one_or_none()
    if not roadmap:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    if roadmap.user_id != user_id:
        raise HTTPException(status_code=403, detail=_FORBIDDEN)

    campaigns_result = await db.execute(
        select(Campaign).where(Campaign.roadmap_id == roadmap_id)
    )
    campaigns = campaigns_result.scalars().all()

    campaign_summaries = [
        CampaignSummary(
            id=c.id,
            campaign_type=_platform_hint(c),
            platform_hint=_platform_hint(c),
            x_post=c.x_post[:100] if c.x_post else None,
            linkedin_post=c.linkedin_post[:100] if c.linkedin_post else None,
            blog_title=_blog_title(c),
            image_url=c.image_url,
            status=c.status.value if isinstance(c.status, RoadmapStatus) else str(c.status),
            scheduled_for=c.scheduled_at,
        )
        for c in campaigns
    ]

    return RoadmapStatusResponse(
        id=roadmap.id,
        status=roadmap.status.value if isinstance(roadmap.status, RoadmapStatus) else str(roadmap.status),
        error_message=roadmap.error_message,
        generate_images=roadmap.generate_images,
        skip_blog=roadmap.skip_blog,
        week_start_date=roadmap.week_start_date,
        campaigns=campaign_summaries,
    )
