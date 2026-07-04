import uuid

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
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
