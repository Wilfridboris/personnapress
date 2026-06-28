from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.connection import get_session
from app.schemas.subscription import SubscriptionResponse
from app.services.subscription_service import create_billing_portal_session, get_subscription

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/me", response_model=SubscriptionResponse)
async def get_my_subscription(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> SubscriptionResponse:
    return await get_subscription(current_user["user_id"], db)


@router.post("/portal")
async def create_portal_session(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    portal_url = await create_billing_portal_session(current_user["user_id"], db)
    return {"portal_url": portal_url}
