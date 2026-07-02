import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.dependencies import get_current_user
from app.db.connection import get_session
from app.db.repositories.campaigns import create_campaign, get_campaign
from app.db.repositories.clients import get_client
from app.db.repositories.jobs import create_job
from app.db.repositories.models import Campaign, Client
from app.schemas.campaign import CampaignCreate, CampaignCreateResponse, CampaignResponse
from app.services.subscription_service import check_campaign_limit
from app.workers.generate import run_generation

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
