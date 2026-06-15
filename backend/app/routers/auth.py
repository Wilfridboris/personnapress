from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection import get_session
from app.schemas.auth import GoogleCallbackRequest, RegisterRequest, ResendVerificationRequest
from app.services.auth_service import (
    auth_google,
    register_user,
    resend_verification,
    verify_email_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=None)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_session)) -> JSONResponse:
    return await register_user(body.email, body.password, db)


@router.get("/verify-email", response_model=None)
async def verify_email(token: str = Query(...), db: AsyncSession = Depends(get_session)) -> JSONResponse:
    return await verify_email_token(token, db)


@router.post("/resend-verification", response_model=None)
async def resend_verification_email(
    body: ResendVerificationRequest, db: AsyncSession = Depends(get_session)
) -> JSONResponse:
    return await resend_verification(body.email, db)


@router.post("/google", response_model=None)
async def google_auth(body: GoogleCallbackRequest, db: AsyncSession = Depends(get_session)) -> JSONResponse:
    return await auth_google(body.google_sub, body.email, body.email_verified, db)
