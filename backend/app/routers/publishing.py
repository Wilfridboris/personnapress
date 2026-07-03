import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.exceptions import PlatformError
from app.core.security import decrypt_credential, encrypt_credential
from app.db.connection import get_session
from app.db.repositories.clients import get_client
from app.db.repositories.platform_connections import (
    delete_connection,
    get_connections_for_client,
    upsert_connection,
)
from app.integrations import webflow as webflow_integration
from app.integrations import wordpress as wordpress_integration

router = APIRouter(prefix="", tags=["publishing"])

ALL_PLATFORMS = ["wordpress", "webflow", "x", "linkedin"]


def _extract_identifier(platform: str, encrypted_credentials: str) -> Optional[str]:
    try:
        data = json.loads(decrypt_credential(encrypted_credentials))
        if platform == "wordpress":
            return data.get("site_url") or None
        if platform == "webflow":
            return data.get("collection_id") or None
        return data.get("handle") or data.get("name") or None
    except Exception:
        return None


def _check_ownership(client, user_id: uuid.UUID) -> None:
    if not client or client.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Client not found.", "detail": {}}},
        )


def _parse_user_id(current_user: dict) -> uuid.UUID:
    try:
        return uuid.UUID(current_user["user_id"])
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "INVALID_SESSION", "message": "Invalid session.", "detail": {}}},
        )


@router.get("/clients/{client_id}/connections")
async def list_platform_connections(
    client_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    user_id = _parse_user_id(current_user)
    client = await get_client(db, client_id)
    _check_ownership(client, user_id)

    connections = await get_connections_for_client(db, client_id)
    connected_map = {pc.platform: pc for pc in connections}

    items = []
    for platform in ALL_PLATFORMS:
        if platform in connected_map:
            pc = connected_map[platform]
            items.append({
                "platform": platform,
                "connected": True,
                "account_identifier": _extract_identifier(platform, pc.encrypted_credentials),
            })
        else:
            items.append({"platform": platform, "connected": False})

    return {"items": items}


class ConnectionCreate(BaseModel):
    platform: str
    # WordPress fields
    site_url: Optional[str] = None
    credential: Optional[str] = None
    username: Optional[str] = None
    # Webflow fields
    token: Optional[str] = None
    collection_id: Optional[str] = None
    # X/LinkedIn fields (Story 5.2)
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    handle: Optional[str] = None


@router.post("/clients/{client_id}/connections", status_code=201)
async def create_platform_connection(
    client_id: uuid.UUID,
    body: ConnectionCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    user_id = _parse_user_id(current_user)
    client = await get_client(db, client_id)
    _check_ownership(client, user_id)

    if body.platform == "wordpress":
        if not body.site_url or not body.credential:
            raise HTTPException(
                status_code=400,
                detail={"error": {"code": "MISSING_FIELDS", "message": "site_url and credential are required for WordPress.", "detail": {}}},
            )
        username = body.username or "admin"
        try:
            await wordpress_integration.validate_credentials(body.site_url, username, body.credential)
        except PlatformError as e:
            raise HTTPException(
                status_code=400,
                detail={"error": {"code": "CREDENTIAL_VALIDATION_FAILED", "message": f"WordPress returned {e.status_code} — {e.message}", "detail": {}}},
            )
        cred_json = json.dumps({"site_url": body.site_url, "username": username, "credential": body.credential})
        account_identifier = body.site_url

    elif body.platform == "webflow":
        if not body.token or not body.collection_id:
            raise HTTPException(
                status_code=400,
                detail={"error": {"code": "MISSING_FIELDS", "message": "token and collection_id are required for Webflow.", "detail": {}}},
            )
        try:
            await webflow_integration.validate_token(body.token)
        except PlatformError as e:
            raise HTTPException(
                status_code=400,
                detail={"error": {"code": "CREDENTIAL_VALIDATION_FAILED", "message": f"Webflow returned {e.status_code} — {e.message}", "detail": {}}},
            )
        cred_json = json.dumps({"token": body.token, "collection_id": body.collection_id})
        account_identifier = body.collection_id

    else:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "UNSUPPORTED_PLATFORM", "message": f"Platform '{body.platform}' is not supported in this endpoint.", "detail": {}}},
        )

    encrypted = encrypt_credential(cred_json)
    await upsert_connection(db, client_id, body.platform, encrypted)

    return {"platform": body.platform, "connected": True, "account_identifier": account_identifier}


@router.get("/clients/{client_id}/webflow/collections")
async def get_webflow_collections(
    client_id: uuid.UUID,
    token: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    user_id = _parse_user_id(current_user)
    client = await get_client(db, client_id)
    _check_ownership(client, user_id)

    try:
        collections = await webflow_integration.fetch_collections(token)
    except PlatformError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "WEBFLOW_API_ERROR", "message": f"Webflow returned {e.status_code} — {e.message}", "detail": {}}},
        )

    return {"collections": collections}


@router.delete("/clients/{client_id}/connections/{platform}", status_code=204)
async def delete_platform_connection(
    client_id: uuid.UUID,
    platform: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    user_id = _parse_user_id(current_user)
    client = await get_client(db, client_id)
    _check_ownership(client, user_id)

    deleted = await delete_connection(db, client_id, platform)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Connection not found.", "detail": {}}},
        )
