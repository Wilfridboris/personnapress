import uuid
from typing import Optional

import nh3
from bs4 import BeautifulSoup
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.dependencies import get_current_user
from app.core.html_sanitize import is_allowed_image_src
from app.db.connection import get_session
from app.db.repositories.campaigns import create_campaign, get_campaign
from app.db.repositories.clients import get_client
from app.db.repositories.jobs import create_job, get_publish_job_for_campaign
from app.db.repositories.models import Article, Campaign, Client
from app.schemas.campaign import CampaignCreate, CampaignCreateResponse, CampaignDetailResponse, CampaignListResponse, CampaignPatch, CampaignResponse
from app.services import image as image_service
from app.services.subscription_service import check_campaign_limit, check_trial_not_expired
from app.workers.generate import run_generation


_ALLOWED_HTML_TAGS = {"h1", "h2", "h3", "h4", "p", "ul", "ol", "li", "strong", "em", "a", "br", "blockquote", "code", "pre", "img", "figure", "figcaption"}
_ALLOWED_HTML_ATTRS: dict[str, set[str]] = {"a": {"href", "title", "rel"}, "img": {"src", "alt", "width", "height"}}
_ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}
_PATCHABLE_FIELDS = frozenset({"blog_html", "x_post", "linkedin_post"})


def _nh3_attribute_filter(tag: str, attr: str, value: str) -> Optional[str]:
    """Filter img src to own-bucket URLs only; pass all other attributes through."""
    if tag == "img" and attr == "src":
        return value if is_allowed_image_src(value) else None
    return value


def _sanitize_blog_html(html: str) -> str:
    """Sanitize blog HTML through nh3, then remove any <img> left without a src."""
    cleaned = nh3.clean(
        html,
        tags=_ALLOWED_HTML_TAGS,
        attributes=_ALLOWED_HTML_ATTRS,
        attribute_filter=_nh3_attribute_filter,
        url_schemes=_ALLOWED_URL_SCHEMES,
        link_rel=None,
    )
    # Post-pass: nh3 strips a disallowed src attribute but leaves the tag; remove empty-src imgs
    soup = BeautifulSoup(cleaned, "html.parser")
    for img in soup.find_all("img"):
        if not img.get("src"):
            img.decompose()
    return str(soup)


class ImageRegenerateResponse(BaseModel):
    image_url: str
    image_regen_count: int


class ApproveResponse(BaseModel):
    id: uuid.UUID
    status: str
    client_id: uuid.UUID


class RejectRequest(BaseModel):
    reason: Optional[str] = None


class RejectResponse(BaseModel):
    id: uuid.UUID
    status: str
    rejection_reason: Optional[str]


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

    await check_trial_not_expired(user_id, db, "create campaigns")
    await check_campaign_limit(db, user_id)

    campaign = await create_campaign(
        db,
        body.client_id,
        body.brain_dump,
        target_keyword=body.target_keyword,
        target_audience=body.target_audience,
    )
    job = await create_job(db, job_type="generation", status="pending", campaign_id=campaign.id)

    await db.commit()

    background_tasks.add_task(run_generation, job.id)

    return CampaignCreateResponse(campaign_id=campaign.id, job_id=job.id)


@router.get("", response_model=CampaignListResponse)
async def list_campaigns(
    client_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> CampaignListResponse:
    try:
        user_id = uuid.UUID(current_user["user_id"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail=_INVALID_SESSION)

    query = (
        select(Campaign)
        .join(Client, Campaign.client_id == Client.id)
        .where(Client.user_id == user_id)
    )
    if client_id:
        client = await get_client(db, client_id)
        if not client or client.user_id != user_id:
            raise HTTPException(status_code=403, detail={"error": {"code": "FORBIDDEN", "message": "Access denied.", "detail": {}}})
        query = query.where(Campaign.client_id == client_id)
    if status:
        statuses = [s.strip() for s in status.split(",") if s.strip()]
        query = query.where(Campaign.status.in_(statuses))

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    ordered_query = query.order_by(Campaign.created_at.desc())
    result = await db.execute(
        ordered_query
             .offset((page - 1) * per_page)
             .limit(per_page)
    )
    campaigns = result.scalars().all()
    return CampaignListResponse(items=[CampaignResponse.model_validate(c) for c in campaigns], total=total)


@router.get("/{campaign_id}", response_model=CampaignDetailResponse)
async def get_campaign_by_id(
    campaign_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> CampaignDetailResponse:
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

    publish_job = await get_publish_job_for_campaign(db, campaign_id)

    article_result = await db.execute(
        select(Article.id, Article.slug).where(Article.campaign_id == campaign_id)
    )
    article_row = article_result.first()

    return CampaignDetailResponse.model_validate(
        {
            **campaign.__dict__,
            "publish_job": publish_job,
            "article_id": article_row[0] if article_row else None,
            "article_slug": article_row[1] if article_row else None,
        }
    )


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
        sanitized = _sanitize_blog_html(patch_data["blog_html"])
        patch_data["blog_html"] = sanitized or None

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

    await check_trial_not_expired(user_id, db, "generate content")

    new_url, regen_count = await image_service.regenerate_image(campaign_id, user_id, db)
    return ImageRegenerateResponse(image_url=new_url, image_regen_count=regen_count)


_INVALID_TRANSITION = {"error": {"code": "INVALID_STATUS_TRANSITION", "message": "Campaign can only be approved from pending_approval status.", "detail": {}}}


@router.post("/{campaign_id}/approve", response_model=ApproveResponse)
async def approve_campaign(
    campaign_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> ApproveResponse:
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
        raise HTTPException(status_code=400, detail=_INVALID_TRANSITION)

    campaign.status = "approved"
    campaign.rejection_reason = None
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)

    return ApproveResponse(id=campaign.id, status=campaign.status, client_id=campaign.client_id)


@router.post("/{campaign_id}/reject", response_model=RejectResponse)
async def reject_campaign(
    campaign_id: uuid.UUID,
    body: RejectRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> RejectResponse:
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
            detail={"error": {"code": "INVALID_STATUS_TRANSITION", "message": "Campaign can only be rejected from pending_approval status.", "detail": {}}},
        )

    campaign.status = "rejected"
    stripped_reason = body.reason.strip() if body.reason else None
    campaign.rejection_reason = stripped_reason if stripped_reason else None

    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)

    return RejectResponse(id=campaign.id, status=campaign.status, rejection_reason=campaign.rejection_reason)


@router.post("/{campaign_id}/regenerate", response_model=CampaignCreateResponse, status_code=202)
async def regenerate_campaign(
    campaign_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> CampaignCreateResponse:
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

    if campaign.status != "rejected":
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_STATUS_TRANSITION", "message": "Only rejected campaigns can be regenerated.", "detail": {}}},
        )

    await check_trial_not_expired(user_id, db, "generate content")
    await check_campaign_limit(db, user_id)

    new_campaign = await create_campaign(db, campaign.client_id, campaign.brain_dump)
    new_job = await create_job(db, job_type="generation", status="pending", campaign_id=new_campaign.id)

    await db.commit()

    background_tasks.add_task(run_generation, new_job.id)

    return CampaignCreateResponse(campaign_id=new_campaign.id, job_id=new_job.id)
