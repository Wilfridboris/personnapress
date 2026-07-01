"""File upload and management router.

POST   /api/v1/clients/{client_id}/files  — upload content files
GET    /api/v1/clients/{client_id}/files  — list uploaded files
DELETE /api/v1/clients/{client_id}/files/{filename}  — delete a file
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi import status as http_status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.dependencies import get_current_user
from app.db.connection import get_session
from app.db.repositories.models import Client
from app.integrations import supabase_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clients", tags=["files"])

_INVALID_SESSION = {"error": {"code": "INVALID_SESSION", "message": "Invalid session.", "detail": {}}}
_NOT_FOUND = {"error": {"code": "CLIENT_NOT_FOUND", "message": "Client not found.", "detail": {}}}
_FORBIDDEN = {"error": {"code": "FORBIDDEN", "message": "Access denied.", "detail": {}}}

FILE_LIMIT = 10
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {".txt", ".md", ".docx"}
BUCKET = "brand-content"


# ── Schemas ──────────────────────────────────────────────────────────────────

class UploadedFile(BaseModel):
    filename: str
    size: int
    path: str


class UploadError(BaseModel):
    filename: str
    error: str


class FileUploadResponse(BaseModel):
    uploaded: list[UploadedFile]
    errors: list[UploadError]


class FileItem(BaseModel):
    filename: str
    size: int


class FileListResponse(BaseModel):
    files: list[FileItem]
    count: int
    limit: int


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ext(filename: str) -> str:
    lower = filename.lower()
    for ext in ALLOWED_EXTENSIONS:
        if lower.endswith(ext):
            return ext
    return ""


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


async def _count_existing_files(client_id: uuid.UUID) -> int:
    try:
        files = await supabase_storage.list_files(BUCKET, f"{client_id}/")
        return len(files)
    except Exception:
        return 0


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post(
    "/{client_id}/files",
    response_model=FileUploadResponse,
    status_code=http_status.HTTP_200_OK,
)
async def upload_files(
    client_id: uuid.UUID,
    files: list[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> FileUploadResponse:
    """Upload up to 10 content files per client (.txt, .md, .docx, max 5 MB each)."""
    await _get_owned_client(client_id, current_user, db)

    existing_count = await _count_existing_files(client_id)

    uploaded: list[UploadedFile] = []
    errors: list[UploadError] = []

    for upload in files:
        filename = upload.filename or "unknown"

        # Extension check
        if not _ext(filename):
            errors.append(
                UploadError(filename=filename, error="Only .txt, .md, and .docx files are supported.")
            )
            continue

        # Read bytes (size check)
        file_bytes = await upload.read()
        if len(file_bytes) > MAX_FILE_SIZE:
            errors.append(UploadError(filename=filename, error="File must be under 5 MB."))
            continue

        # Count check (server-side)
        if existing_count + len(uploaded) >= FILE_LIMIT:
            errors.append(
                UploadError(
                    filename=filename,
                    error="You've reached the 10-file limit for this client.",
                )
            )
            continue

        path = f"{client_id}/{filename}"
        try:
            await supabase_storage.upload_file(BUCKET, path, file_bytes)
            uploaded.append(UploadedFile(filename=filename, size=len(file_bytes), path=path))
        except Exception as exc:
            logger.warning("Failed to upload %s for client %s: %s", filename, client_id, exc)
            errors.append(UploadError(filename=filename, error="Upload failed. Please try again."))

    return FileUploadResponse(uploaded=uploaded, errors=errors)


@router.get("/{client_id}/files", response_model=FileListResponse)
async def list_client_files(
    client_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> FileListResponse:
    """List uploaded content files for a client."""
    await _get_owned_client(client_id, current_user, db)

    try:
        raw_files = await supabase_storage.list_files(BUCKET, f"{client_id}/")
    except Exception as exc:
        logger.warning("list_client_files: failed to list files for client %s: %s", client_id, exc)
        raw_files = []

    items: list[FileItem] = []
    for f in raw_files:
        name = f.get("name", "")
        size = 0
        metadata = f.get("metadata") or {}
        if isinstance(metadata, dict):
            size = int(metadata.get("size", 0))
        if name:
            items.append(FileItem(filename=name, size=size))

    return FileListResponse(files=items, count=len(items), limit=FILE_LIMIT)


@router.delete("/{client_id}/files/{filename}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_client_file(
    client_id: uuid.UUID,
    filename: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> Response:
    """Delete an uploaded content file (stub v1 — deletes from Supabase Storage)."""
    await _get_owned_client(client_id, current_user, db)

    path = f"{client_id}/{filename}"
    try:
        await supabase_storage.delete_file(BUCKET, path)
    except Exception as exc:
        logger.warning("delete_client_file: failed to delete %s: %s", path, exc)
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "DELETE_FAILED", "message": "Failed to delete file.", "detail": {}}},
        )

    return Response(status_code=http_status.HTTP_204_NO_CONTENT)
