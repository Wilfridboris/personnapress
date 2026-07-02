import uuid
from typing import Union
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.connection import get_session
from app.db.repositories.clients import (
    create_client,
    delete_client,
    get_campaign_count,
    get_client,
    get_clients_by_user,
    update_client,
)
from app.db.repositories.jobs import (
    create_job,
    get_active_ingestion_job_for_client,
    get_latest_voice_job_for_client,
)
from app.schemas.client import (
    ClientCreate,
    ClientListItem,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
    QuestionnaireRequest,
)
from app.services.subscription_service import check_client_limit, get_user_plan_info
from app.workers.ingest import ingest_worker, questionnaire_worker

router = APIRouter(prefix="/clients", tags=["clients"])

_INVALID_SESSION = {"error": {"code": "INVALID_SESSION", "message": "Invalid session.", "detail": {}}}
_NOT_FOUND = {"error": {"code": "CLIENT_NOT_FOUND", "message": "Client not found.", "detail": {}}}
_FORBIDDEN = {"error": {"code": "FORBIDDEN", "message": "Access denied.", "detail": {}}}


def _extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc or url
    except Exception:
        return url


@router.get("", response_model=ClientListResponse)
async def list_clients(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> ClientListResponse:
    try:
        user_id = uuid.UUID(current_user["user_id"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail=_INVALID_SESSION)

    plan_tier, client_limit = await get_user_plan_info(user_id, db)
    rows = await get_clients_by_user(db, user_id)

    clients = []
    for client, campaign_count, has_active_ingestion in rows:
        if has_active_ingestion:
            bvp_status = "analyzing"
        elif client.brand_voice_profile is not None:
            bvp_status = "ready"
        else:
            bvp_status = "incomplete"

        clients.append(ClientListItem(
            id=client.id,
            name=client.name,
            website_url=client.website_url,
            brand_voice_profile_status=bvp_status,
            campaign_count=campaign_count or 0,
        ))

    return ClientListResponse(
        clients=clients,
        plan_at_limit=len(clients) >= client_limit,
        plan_tier=plan_tier,
        client_limit=client_limit,
    )


@router.post("", response_model=ClientResponse, status_code=201)
async def create_new_client(
    body: ClientCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> ClientResponse:
    try:
        user_id = uuid.UUID(current_user["user_id"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail=_INVALID_SESSION)

    await check_client_limit(user_id, db)

    client = await create_client(db, user_id, body.name, body.website_url)

    job_id: uuid.UUID | None = None
    if body.website_url:
        job = await create_job(db, job_type="ingestion", status="pending", client_id=client.id)
        job_id = job.id
        background_tasks.add_task(ingest_worker, job_id=job.id, client_id=client.id)

    await db.commit()

    return ClientResponse(
        id=client.id,
        name=client.name,
        website_url=client.website_url,
        brand_voice_profile=client.brand_voice_profile,
        job_id=job_id,
        campaign_count=0,
        created_at=client.created_at,
    )


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client_detail(
    client_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> ClientResponse:
    try:
        user_id = uuid.UUID(current_user["user_id"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail=_INVALID_SESSION)

    client = await get_client(db, client_id)
    if not client or client.user_id != user_id:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)

    active_job = await get_active_ingestion_job_for_client(db, client_id)
    latest_job = await get_latest_voice_job_for_client(db, client_id)
    campaign_count = await get_campaign_count(db, client_id)

    _job_failed_no_content = (
        active_job is None
        and latest_job is not None
        and latest_job.status == "failed"
        and latest_job.error_details == "no_content"
        and client.brand_voice_profile is None
    )
    ingestion_no_content = _job_failed_no_content
    ingestion_failed = (
        active_job is None
        and latest_job is not None
        and latest_job.status == "failed"
        and latest_job.error_details != "no_content"
        and client.brand_voice_profile is None
    )

    return ClientResponse(
        id=client.id,
        name=client.name,
        website_url=client.website_url,
        brand_voice_profile=client.brand_voice_profile,
        job_id=active_job.id if active_job else None,
        campaign_count=campaign_count,
        created_at=client.created_at,
        ingestion_failed=ingestion_failed,
        ingestion_no_content=ingestion_no_content,
        ingestion_error=latest_job.error_details if ingestion_failed and latest_job else None,
    )


@router.patch("/{client_id}", response_model=Union[ClientResponse, dict])
async def update_client_detail(
    client_id: uuid.UUID,
    body: ClientUpdate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> Union[ClientResponse, dict]:
    try:
        user_id = uuid.UUID(current_user["user_id"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail=_INVALID_SESSION)

    client = await get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    if client.user_id != user_id:
        raise HTTPException(status_code=403, detail=_FORBIDDEN)

    url_changed = body.website_url is not None and body.website_url != client.website_url

    if url_changed and not body.confirm_url_change:
        # Frontend must show re-analyze dialog before resubmitting
        return {"requires_confirmation": True, "domain": _extract_domain(body.website_url)}

    update_fields: dict = {}
    if body.name is not None:
        update_fields["name"] = body.name
    if body.brand_voice_profile is not None:
        update_fields["brand_voice_profile"] = body.brand_voice_profile

    if not update_fields and not url_changed:
        # Nothing to change — return current state without touching the DB
        active_job = await get_active_ingestion_job_for_client(db, client_id)
        campaign_count = await get_campaign_count(db, client_id)
        return ClientResponse(
            id=client.id,
            name=client.name,
            website_url=client.website_url,
            brand_voice_profile=client.brand_voice_profile,
            job_id=active_job.id if active_job else None,
            campaign_count=campaign_count,
            created_at=client.created_at,
        )

    job_id: uuid.UUID | None = None

    if url_changed and body.confirm_url_change:
        update_fields["website_url"] = body.website_url
        update_fields["brand_voice_profile"] = None
        updated = await update_client(db, client_id, **update_fields)
        if not updated:
            raise HTTPException(status_code=404, detail=_NOT_FOUND)
        job = await create_job(db, job_type="ingestion", status="pending", client_id=client_id)
        job_id = job.id
        background_tasks.add_task(ingest_worker, job_id=job.id, client_id=client_id)
    else:
        updated = await update_client(db, client_id, **update_fields)
        if not updated:
            raise HTTPException(status_code=404, detail=_NOT_FOUND)

    await db.commit()

    active_job = await get_active_ingestion_job_for_client(db, client_id) if not job_id else None
    campaign_count = await get_campaign_count(db, client_id)

    return ClientResponse(
        id=updated.id,
        name=updated.name,
        website_url=updated.website_url,
        brand_voice_profile=updated.brand_voice_profile,
        job_id=job_id or (active_job.id if active_job else None),
        campaign_count=campaign_count,
        created_at=updated.created_at,
    )


@router.delete("/{client_id}", status_code=204)
async def delete_client_detail(
    client_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> Response:
    try:
        user_id = uuid.UUID(current_user["user_id"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail=_INVALID_SESSION)

    client = await get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    if client.user_id != user_id:
        raise HTTPException(status_code=403, detail=_FORBIDDEN)

    await delete_client(db, client_id)
    await db.commit()

    return Response(status_code=204)


@router.post("/{client_id}/questionnaire", status_code=202)
async def submit_voice_questionnaire(
    client_id: uuid.UUID,
    body: QuestionnaireRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    """Submit a voice questionnaire and kick off Gemini extraction.

    Returns ``{job_id}`` immediately (HTTP 202).  The frontend polls the job
    until it reaches a terminal state and then refreshes the voice setup page.
    """
    try:
        user_id = uuid.UUID(current_user["user_id"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail=_INVALID_SESSION)

    client = await get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    if client.user_id != user_id:
        raise HTTPException(status_code=403, detail=_FORBIDDEN)

    active_job = await get_active_ingestion_job_for_client(db, client_id)
    if active_job:
        return {"job_id": str(active_job.id)}

    job = await create_job(
        db, job_type="questionnaire", status="pending", client_id=client_id
    )
    await db.commit()

    background_tasks.add_task(
        questionnaire_worker,
        job_id=job.id,
        client_id=client_id,
        questionnaire_data=body,
    )

    return {"job_id": str(job.id)}
