import uuid
from typing import Optional

import nh3
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.dependencies import get_current_user
from app.db.connection import get_session
from app.db.repositories.campaigns import create_campaign, get_campaign
from app.db.repositories.clients import get_client
from app.db.repositories.jobs import create_job
from app.db.repositories.models import Campaign, Client
from app.schemas.campaign import CampaignCreate, CampaignCreateResponse, CampaignPatch, CampaignResponse
from app.services import image as image_service
from app.services.subscription_service import check_campaign_limit
from app.workers.generate import run_generation


_ALLOWED_HTML_TAGS = {"h1", "h2", "h3", "h4", "p", "ul", "ol", "li", "strong", "em", "a", "br", "blockquote", "code", "pre"}
_ALLOWED_HTML_ATTRS: dict[str, set[str]] = {"a": {"href", "title", "rel"}}
_ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}
_PATCHABLE_FIELDS = frozenset({"blog_html", "x_post", "linkedin_post"})


class ImageRegenerateResponse(BaseModel):
    image_url: str
    image_regen_count: int

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

_INVALID_SESSION = {"error": {"code": "INVALID_SESSION", "message": "Invalid session.", "detail": {}}}
_NOT_FOUND = {"error": {"code": "CAMPAIGN_NOT_FOUND", "message": "Campaign not found.", "detail": {}}}


@router.post("", response_model=CampaignCreateResponse, status_code=202)
async def create_new_campaign(
    body: CampaignCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> CampaignCreateResponse:
    try:
        user_id = uuid.UUID(current_user["user_id"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail=_INVALID_SESSION)

    client = await get_client(db, body.client_id)
    if not client or client.user_id != user_id:
        raise HTTPException(status_code=404, detail={"error": {"code": "CLIENT_NOT_FOUND", "message": "Client not found.", "detail": {}}})

    await check_campaign_limit(db, user_id)

    campaign = await create_campaign(db, body.client_id, body.brain_dump)
    job = await create_job(db, job_type="generation", status="pending", campaign_id=campaign.id)

    await db.commit()

    background_tasks.add_task(run_generation, job.id)

    return CampaignCreateResponse(campaign_id=campaign.id, job_id=job.id)


@router.get("", response_model=list[CampaignResponse])
async def list_campaigns(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> list[CampaignResponse]:
    try:
        user_id = uuid.UUID(current_user["user_id"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail=_INVALID_SESSION)

    result = await db.execute(
        select(Campaign)
        .join(Client, Campaign.client_id == Client.id)
        .where(Client.user_id == user_id)
        .order_by(Campaign.created_at.desc())
    )
    campaigns = result.scalars().all()
    return [CampaignResponse.model_validate(c) for c in campaigns]


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign_by_id(
    campaign_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> CampaignResponse:
    try:
        user_id = uuid.UUID(current_user["user_id"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail=_INVALID_SESSION)

    campaign = await get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)

    client = await get_client(db, campaign.client_id)
    if not client or client.user_id != user_id:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)

    return CampaignResponse.model_validate(campaign)


@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def patch_campaign(
    campaign_id: uuid.UUID,
    body: CampaignPatch,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> CampaignResponse:
    try:
        user_id = uuid.UUID(current_user["user_id"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail=_INVALID_SESSION)

    campaign = await get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)

    client = await get_client(db, campaign.client_id)
    if not client or client.user_id != user_id:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)

    if campaign.status != "pending_approval":
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_STATUS_FOR_EDIT", "message": "Campaign content can only be edited while pending approval.", "detail": {}}},
        )

    patch_data = {k: v for k, v in body.model_dump(exclude_none=True).items() if k in _PATCHABLE_FIELDS}
    if "blog_html" in patch_data:
        patch_data["blog_html"] = nh3.clean(
            patch_data["blog_html"],
            tags=_ALLOWED_HTML_TAGS,
            attributes=_ALLOWED_HTML_ATTRS,
            url_schemes=_ALLOWED_URL_SCHEMES,
        )

    for key, value in patch_data.items():
        setattr(campaign, key, value)

    if patch_data:
        db.add(campaign)
        await db.commit()
        await db.refresh(campaign)

    return CampaignResponse.model_validate(campaign)


@router.post("/{campaign_id}/image/regenerate", response_model=ImageRegenerateResponse)
async def regenerate_campaign_image(
    campaign_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> ImageRegenerateResponse:
    try:
        user_id = uuid.UUID(current_user["user_id"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail=_INVALID_SESSION)

    campaign = await get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)

    client = await get_client(db, campaign.client_id)
    if not client or client.user_id != user_id:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)

    new_url, regen_count = await image_service.regenerate_image(campaign_id, user_id, db)
    return ImageRegenerateResponse(image_url=new_url, image_regen_count=regen_count)
