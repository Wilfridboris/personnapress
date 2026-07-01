import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.connection import get_session
from app.db.repositories.clients import create_client, get_client
from app.db.repositories.jobs import create_job, get_active_ingestion_job_for_client
from app.schemas.client import ClientCreate, ClientResponse
from app.services.subscription_service import check_client_limit
from app.workers.ingest import ingest_worker

router = APIRouter(prefix="/clients", tags=["clients"])

_INVALID_SESSION = {"error": {"code": "INVALID_SESSION", "message": "Invalid session.", "detail": {}}}


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
        raise HTTPException(status_code=404, detail={"error": {"code": "CLIENT_NOT_FOUND", "message": "Client not found.", "detail": {}}})

    active_job = await get_active_ingestion_job_for_client(db, client_id)

    return ClientResponse(
        id=client.id,
        name=client.name,
        website_url=client.website_url,
        brand_voice_profile=client.brand_voice_profile,
        job_id=active_job.id if active_job else None,
        created_at=client.created_at,
    )
