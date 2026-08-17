import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.db.connection import get_session
from app.db.repositories.clients import get_client
from app.schemas.analytics import ClientPostMetricsResponse, ClientSummaryResponse
from app.services.analytics import get_client_post_metrics, get_client_summary
from starlette.requests import Request

router = APIRouter(prefix="/analytics", tags=["analytics"])

_INVALID_SESSION = {"error": {"code": "INVALID_SESSION", "message": "Invalid session.", "detail": {}}}
_CLIENT_NOT_FOUND = {"error": {"code": "CLIENT_NOT_FOUND", "message": "Client not found.", "detail": {}}}


def _resolve_user_id(current_user: dict) -> uuid.UUID:
    try:
        return uuid.UUID(current_user["user_id"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail=_INVALID_SESSION)


async def _verify_client(
    db: AsyncSession,
    client_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    client = await get_client(db, client_id)
    if not client or client.user_id != user_id:
        raise HTTPException(status_code=404, detail=_CLIENT_NOT_FOUND)


@router.get(
    "/clients/{client_id}/summary",
    response_model=ClientSummaryResponse,
)
@limiter.limit("10/minute")
async def client_analytics_summary(
    request: Request,
    client_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> ClientSummaryResponse:
    user_id = _resolve_user_id(current_user)
    await _verify_client(db, client_id, user_id)
    return await get_client_summary(db, client_id)


@router.get(
    "/clients/{client_id}/posts",
    response_model=ClientPostMetricsResponse,
)
@limiter.limit("10/minute")
async def client_post_metrics(
    request: Request,
    client_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> ClientPostMetricsResponse:
    user_id = _resolve_user_id(current_user)
    await _verify_client(db, client_id, user_id)
    return await get_client_post_metrics(db, client_id)
