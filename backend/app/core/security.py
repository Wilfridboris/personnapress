import base64
import os
import uuid
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError

from app.core.config import settings

ALGORITHM = "HS256"
SESSION_EXPIRY_DAYS = 7
VERIFICATION_EXPIRY_HOURS = 24


def create_session_token(
    user_id: uuid.UUID,
    email: str,
    plan_tier: str,
    verified: bool,
    onboarding_completed: bool = False,
) -> str:
    payload = {
        "user_id": str(user_id),
        "email": email,
        "plan_tier": plan_tier,
        "verified": verified,
        "onboarding_completed": onboarding_completed,
        "exp": datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRY_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_session_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired.")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid session token.")


def create_verification_token(email: str) -> str:
    payload = {
        "sub": email,
        "type": "email_verification",
        "exp": datetime.now(timezone.utc) + timedelta(hours=VERIFICATION_EXPIRY_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_verification_token(token: str) -> str:
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
    if payload.get("type") != "email_verification":
        raise JWTError("Invalid token type")
    sub: str | None = payload.get("sub")
    if not sub:
        raise JWTError("Missing subject")
    return sub


def set_session_cookie(response: JSONResponse, token: str) -> None:
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 24 * SESSION_EXPIRY_DAYS,
        path="/",
    )


def _get_key() -> bytes:
    key = settings.CREDENTIAL_ENCRYPTION_KEY.encode()
    return key[:32].ljust(32, b"\x00")


def encrypt_credential(plaintext: str) -> str:
    key = _get_key()
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ciphertext).decode()


def decrypt_credential(encoded: str) -> str:
    key = _get_key()
    data = base64.b64decode(encoded)
    nonce, ciphertext = data[:12], data[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None).decode()
