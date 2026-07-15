import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from jose import JWTError
from jose.exceptions import ExpiredSignatureError
import bcrypt as _bcrypt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.core.security import (
    create_session_token,
    create_verification_token,
    decode_verification_token,
    set_session_cookie,
)
from app.db.repositories.models import Subscription, User
from app.integrations.email import send_verification_email

logger = logging.getLogger(__name__)

_DUMMY_HASH = _bcrypt.hashpw(b"dummy", _bcrypt.gensalt())


def _hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return _bcrypt.checkpw(password.encode(), hashed.encode())


def _dummy_verify() -> None:
    _bcrypt.checkpw(b"dummy", _DUMMY_HASH)


def _err(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message, "detail": {}}}


def logout_user() -> JSONResponse:
    response = JSONResponse({"success": True})
    response.delete_cookie(
        key="session",
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
        domain=settings.COOKIE_DOMAIN,
    )
    return response


async def _new_subscription(user_id: uuid.UUID, db: AsyncSession) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    sub = Subscription(
        user_id=user_id,
        plan_tier="growth",
        status="trialing",
        campaigns_used=0,
        clients_count=0,
        image_gen_used=0,
        billing_cycle_start=now,
        billing_cycle_end=now + timedelta(days=settings.TRIAL_DAYS),
    )
    db.add(sub)


async def _issue_session(user: User, db: AsyncSession) -> JSONResponse:
    result_sub = await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    sub = result_sub.scalar_one_or_none()
    plan_tier = sub.plan_tier if sub else "growth"
    token = create_session_token(
        user.id,
        user.email,
        plan_tier,
        verified=bool(user.verified),
        onboarding_completed=bool(user.onboarding_completed),
    )
    redirect = "/dashboard" if user.onboarding_completed else "/onboarding"
    response = JSONResponse({"redirect_url": redirect})
    set_session_cookie(response, token)
    return response


async def register_user(email: str, password: str, db: AsyncSession) -> JSONResponse:
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=_err("EMAIL_ALREADY_EXISTS", "An account with this email already exists."),
        )

    hashed = _hash_password(password)
    new_user = User(email=email, hashed_password=hashed, verified=False)
    db.add(new_user)
    await db.flush()

    await _new_subscription(new_user.id, db)
    await db.commit()

    verification_token = create_verification_token(email)
    try:
        await asyncio.to_thread(send_verification_email, email, verification_token)
    except Exception:
        logger.exception("Failed to send verification email to %s", email)

    return JSONResponse({"message": "Check your email to verify your account."})


async def verify_email_token(token: str, db: AsyncSession) -> JSONResponse:
    try:
        email = decode_verification_token(token)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=400,
            detail=_err("TOKEN_EXPIRED", "Verification link expired. Request a new one."),
        )
    except JWTError:
        raise HTTPException(
            status_code=400,
            detail=_err("TOKEN_INVALID", "Invalid verification link."),
        )

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=400,
            detail=_err("TOKEN_INVALID", "Invalid verification link."),
        )

    if user.verified:
        return await _issue_session(user, db)

    user.verified = True
    await db.commit()
    await db.refresh(user)
    return await _issue_session(user, db)


async def resend_verification(email: str, db: AsyncSession) -> JSONResponse:
    result = await db.execute(select(User).where(User.email == email, User.verified == False))  # noqa: E712
    user = result.scalar_one_or_none()
    if user:
        verification_token = create_verification_token(email)
        try:
            await asyncio.to_thread(send_verification_email, email, verification_token)
        except Exception:
            logger.exception("Failed to resend verification email to %s", email)
    return JSONResponse({"message": "If that address is registered and unverified, a new email is on its way."})


async def login_user(email: str, password: str, db: AsyncSession) -> JSONResponse:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    # Always run bcrypt to prevent timing-based email enumeration
    if user and user.hashed_password:
        password_ok = _verify_password(password, user.hashed_password)
    else:
        _dummy_verify()
        password_ok = False

    if not password_ok:
        return JSONResponse(
            status_code=401,
            content=_err("INVALID_CREDENTIALS", "Invalid email or password."),
        )

    if not user.verified:
        return JSONResponse(
            status_code=403,
            content=_err("EMAIL_NOT_VERIFIED", "Please verify your email before logging in."),
        )

    result_sub = await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    sub = result_sub.scalar_one_or_none()
    plan_tier = sub.plan_tier if sub else "growth"
    token = create_session_token(
        user.id,
        user.email,
        plan_tier,
        verified=bool(user.verified),
        onboarding_completed=bool(user.onboarding_completed),
    )
    response = JSONResponse({"success": True})
    set_session_cookie(response, token)
    return response


async def auth_google(google_sub: str, email: str, email_verified: bool, db: AsyncSession) -> JSONResponse:
    if not email_verified:
        raise HTTPException(
            status_code=400,
            detail=_err("EMAIL_NOT_VERIFIED", "Google account email is not verified."),
        )

    result = await db.execute(select(User).where(User.google_sub == google_sub))
    user = result.scalar_one_or_none()

    if not user:
        result_by_email = await db.execute(select(User).where(User.email == email))
        user = result_by_email.scalar_one_or_none()

    if user is None:
        user = User(email=email, google_sub=google_sub, verified=True)
        db.add(user)
        await db.flush()
        await _new_subscription(user.id, db)
        await db.commit()
        await db.refresh(user)
    else:
        if not user.google_sub:
            user.google_sub = google_sub
        if not user.verified:
            user.verified = True
        await db.commit()
        await db.refresh(user)

    return await _issue_session(user, db)


async def complete_onboarding(user_id: uuid.UUID, db: AsyncSession) -> JSONResponse:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=_err("NOT_FOUND", "User not found."))

    user.onboarding_completed = True
    await db.commit()

    result_sub = await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    sub = result_sub.scalar_one_or_none()
    plan_tier = sub.plan_tier if sub else "growth"
    token = create_session_token(
        user.id,
        user.email,
        plan_tier,
        verified=bool(user.verified),
        onboarding_completed=True,
    )
    response = JSONResponse({"status": "ok"})
    set_session_cookie(response, token)
    return response
