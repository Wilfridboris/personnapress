"""Image upload router.

POST /api/v1/clients/{client_id}/images  — upload a single user image (png/jpg/jpeg/webp)
"""

import logging
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi import status as http_status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.dependencies import get_current_user
from app.db.connection import get_session
from app.db.repositories.models import Client
from app.integrations import supabase_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clients", tags=["images"])

_INVALID_SESSION = {"error": {"code": "INVALID_SESSION", "message": "Invalid session.", "detail": {}}}
_NOT_FOUND = {"error": {"code": "CLIENT_NOT_FOUND", "message": "Client not found.", "detail": {}}}
_FORBIDDEN = {"error": {"code": "FORBIDDEN", "message": "Access denied.", "detail": {}}}

BUCKET = "article-images"
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB
_ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

# Magic-byte signatures for supported formats
_MAGIC = {
    ".png": b"\x89PNG\r\n\x1a\n",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".webp": None,  # checked separately: RIFF....WEBP
}


class ImageUploadResponse(BaseModel):
    url: str
    path: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_ext(filename: str) -> str:
    lower = filename.lower()
    for ext in _ALLOWED_EXTS:
        if lower.endswith(ext):
            return ext
    return ""


def _check_magic(ext: str, data: bytes) -> bool:
    """Validate magic bytes match the declared extension."""
    if ext == ".webp":
        return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    prefix = _MAGIC.get(ext)
    if prefix is None:
        return False
    return data[:len(prefix)] == prefix


async def _get_owned_client(
    client_id: uuid.UUID,
    current_user: dict,
    db: AsyncSession,
) -> Client:
    try:
        user_id = uuid.UUID(current_user["user_id"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail=_INVALID_SESSION)

    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    if client.user_id != user_id:
        raise HTTPException(status_code=403, detail=_FORBIDDEN)
    return client


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post(
    "/{client_id}/images",
    response_model=ImageUploadResponse,
    status_code=http_status.HTTP_200_OK,
)
async def upload_image(
    client_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> ImageUploadResponse:
    """Upload a single image (png/jpg/jpeg/webp, max 5 MB) for use in articles."""
    await _get_owned_client(client_id, current_user, db)

    filename = file.filename or "upload"
    ext = _get_ext(filename)
    if not ext:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_IMAGE_TYPE", "message": "Only .png, .jpg, .jpeg, and .webp files are supported.", "detail": {}}},
        )

    file_bytes = await file.read()

    if len(file_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "FILE_TOO_LARGE", "message": "Image must be under 5 MB.", "detail": {}}},
        )

    if not _check_magic(ext, file_bytes):
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_IMAGE", "message": "File content does not match the declared image type.", "detail": {}}},
        )

    object_path = f"{client_id}/{uuid.uuid4()}{ext}"
    try:
        await supabase_storage.upload_file(BUCKET, object_path, file_bytes, public=True)
    except Exception as exc:
        logger.warning("upload_image: failed for client %s: %s", client_id, exc)
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "UPLOAD_FAILED", "message": "Image upload failed. Please try again.", "detail": {}}},
        ) from exc

    url = supabase_storage.public_object_url(BUCKET, object_path)
    return ImageUploadResponse(url=url, path=object_path)
