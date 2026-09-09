import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.db.connection import get_session
from app.schemas.auth import GoogleCallbackRequest, LoginRequest, RegisterRequest, ResendVerificationRequest
from app.services.auth_service import (
    auth_google,
    complete_onboarding,
    login_user,
    logout_user,
    patch_onboarding_step,
    register_user,
    resend_verification,
    verify_email_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=None)
@limiter.limit("10/minute")
async def register(request: Request, body: RegisterRequest, db: AsyncSession = Depends(get_session)) -> JSONResponse:
    return await register_user(body.email, body.password, db)


@router.get("/verify-email", response_model=None)
async def verify_email(token: str = Query(...), db: AsyncSession = Depends(get_session)) -> JSONResponse:
    return await verify_email_token(token, db)


@router.post("/resend-verification", response_model=None)
@limiter.limit("5/minute")
async def resend_verification_email(
    request: Request, body: ResendVerificationRequest, db: AsyncSession = Depends(get_session)
) -> JSONResponse:
    return await resend_verification(body.email, db)


@router.post("/login", response_model=None)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_session)) -> JSONResponse:
    return await login_user(body.email, body.password, db)


@router.post("/logout", response_model=None)
async def logout() -> JSONResponse:
    return logout_user()


@router.post("/google", response_model=None)
@limiter.limit("20/minute")
async def google_auth(
    request: Request, body: GoogleCallbackRequest, db: AsyncSession = Depends(get_session)
) -> JSONResponse:
    return await auth_google(body.google_sub, body.email, body.email_verified, db)


@router.post("/complete-onboarding", response_model=None)
async def complete_onboarding_endpoint(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> JSONResponse:
    user_id = uuid.UUID(current_user["user_id"])
    return await complete_onboarding(user_id, db)


class OnboardingStepRequest(BaseModel):
    step: int = Field(ge=1, le=4)


@router.patch("/onboarding-step", response_model=None)
async def patch_onboarding_step_endpoint(
    body: OnboardingStepRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Persist the most recently completed onboarding step (1-4).

    Fire-and-forget from the frontend: failure never blocks the UI.
    """
    try:
        user_id = uuid.UUID(current_user["user_id"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail={"error": {"code": "INVALID_SESSION", "message": "Invalid session.", "detail": {}}})
    return await patch_onboarding_step(user_id, body.step, db)
