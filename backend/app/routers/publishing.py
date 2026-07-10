import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

from apscheduler.jobstores.base import JobLookupError
from apscheduler.triggers.date import DateTrigger
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.exceptions import PlatformError
from app.core.security import decrypt_credential, encrypt_credential
from app.db.connection import get_session
from app.db.repositories.campaigns import get_campaign, update_campaign_scheduled_at
from app.db.repositories.clients import get_client
from app.db.repositories.jobs import create_job, get_publish_job_for_campaign, get_scheduled_job
from app.db.repositories.platform_connections import (
    delete_connection,
    get_connections_for_client,
    upsert_connection,
)
from app.integrations import github as github_integration
from app.integrations import linkedin as linkedin_integration
from app.services import repo_detection
from app.integrations import twitter as twitter_integration
from app.integrations import webflow as webflow_integration
from app.integrations import wordpress as wordpress_integration
from app.integrations import wordpress_com as wordpress_com_integration
from app.scheduler.scheduler import scheduler
from app.services.subscription_service import check_trial_not_expired
from app.workers.publish import publish_github_job, run_publish
from app.workers.publish_retry import run_publish_retry

router = APIRouter(prefix="", tags=["publishing"])

ALL_PLATFORMS = ["wordpress", "webflow", "x", "linkedin", "github_pages"]


def _extract_identifier(platform: str, encrypted_credentials: str) -> Optional[str]:
    try:
        data = json.loads(decrypt_credential(encrypted_credentials))
        if platform == "wordpress":
            return data.get("site_url") or None
        if platform == "wordpress-com":
            return data.get("blog_url") or None
        if platform == "webflow":
            return data.get("collection_id") or None
        if platform == "github_pages":
            return data.get("repo_full_name") or None
        return data.get("handle") or data.get("name") or None
    except Exception:
        return None


def _extract_github_detection(encrypted_credentials: str) -> Optional[dict]:
    try:
        data = json.loads(decrypt_credential(encrypted_credentials))
        detected_framework = data.get("detected_framework")
        if not detected_framework:
            return None
        return {
            "detected_framework": detected_framework,
            "publish_path": data.get("publish_path", ""),
            "confidence": data.get("confidence", "low"),
            "signals": data.get("signals", []),
            "candidates": data.get("candidates", []),
        }
    except Exception:
        logger.warning("Failed to extract github detection from credentials", exc_info=True)
        return None


def _extract_direct_commit_default(encrypted_credentials: str) -> bool:
    try:
        data = json.loads(decrypt_credential(encrypted_credentials))
        return bool(data.get("direct_commit_default", False))
    except Exception:
        logger.warning("Failed to extract direct_commit_default from GitHub credentials", exc_info=True)
        return False


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
            item: dict = {
                "platform": platform,
                "connected": True,
                "account_identifier": _extract_identifier(platform, pc.encrypted_credentials),
            }
            if platform == "github_pages":
                item["github_detection"] = _extract_github_detection(pc.encrypted_credentials)
                item["direct_commit_default"] = _extract_direct_commit_default(pc.encrypted_credentials)
            items.append(item)
        elif platform == "wordpress" and "wordpress-com" in connected_map:
            # WordPress.com connection shown under the wordpress card
            pc = connected_map["wordpress-com"]
            items.append({
                "platform": "wordpress",
                "connected": True,
                "account_identifier": _extract_identifier("wordpress-com", pc.encrypted_credentials),
                "connected_via": "wordpress-com",
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


class OAuthCallbackRequest(BaseModel):
    code: str
    code_verifier: Optional[str] = None


def _platform_error_msg(e: Exception) -> str:
    """Extract a safe, serializable message from a platform exception."""
    msg = getattr(e, "message", None)
    return str(msg) if msg is not None else str(e)


@router.post("/clients/{client_id}/connections/x/callback", status_code=201)
async def x_oauth_callback(
    client_id: uuid.UUID,
    body: OAuthCallbackRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    user_id = _parse_user_id(current_user)
    client = await get_client(db, client_id)
    _check_ownership(client, user_id)

    if not body.code_verifier:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "MISSING_CODE_VERIFIER", "message": "code_verifier is required for X OAuth PKCE", "detail": {}}},
        )

    redirect_uri = f"{settings.APP_URL}/api/auth/x/callback"
    try:
        tokens = await twitter_integration.exchange_code_for_tokens(
            body.code, body.code_verifier, redirect_uri
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "TOKEN_EXCHANGE_FAILED", "message": _platform_error_msg(e), "detail": {}}},
        )

    access_token = tokens.get("access_token", "")
    if not access_token:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "TOKEN_EXCHANGE_FAILED", "message": "X token exchange returned no access_token", "detail": {}}},
        )
    refresh_token = tokens.get("refresh_token", "")
    handle = await twitter_integration.get_user_handle(access_token)

    cred_json = json.dumps({"access_token": access_token, "refresh_token": refresh_token, "handle": handle})
    encrypted = encrypt_credential(cred_json)
    await upsert_connection(db, client_id, "x", encrypted)

    return {"platform": "x", "connected": True, "account_identifier": f"@{handle}"}


@router.post("/clients/{client_id}/connections/linkedin/callback", status_code=201)
async def linkedin_oauth_callback(
    client_id: uuid.UUID,
    body: OAuthCallbackRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    user_id = _parse_user_id(current_user)
    client = await get_client(db, client_id)
    _check_ownership(client, user_id)

    redirect_uri = f"{settings.APP_URL}/api/auth/linkedin/callback"
    try:
        access_token = await linkedin_integration.exchange_code_for_token(body.code, redirect_uri)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "TOKEN_EXCHANGE_FAILED", "message": _platform_error_msg(e), "detail": {}}},
        )

    name = await linkedin_integration.get_user_name(access_token)

    cred_json = json.dumps({"access_token": access_token, "name": name})
    encrypted = encrypt_credential(cred_json)
    await upsert_connection(db, client_id, "linkedin", encrypted)

    return {"platform": "linkedin", "connected": True, "account_identifier": name}


class WpComCallbackRequest(BaseModel):
    code: str


@router.post("/clients/{client_id}/connections/wordpress-com/callback", status_code=201)
async def wordpress_com_oauth_callback(
    client_id: uuid.UUID,
    body: WpComCallbackRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    user_id = _parse_user_id(current_user)
    client = await get_client(db, client_id)
    _check_ownership(client, user_id)

    redirect_uri = settings.WP_COM_REDIRECT_URI or f"{settings.APP_URL}/api/auth/wordpress-com/callback"
    try:
        tokens = await wordpress_com_integration.exchange_code_for_tokens(body.code, redirect_uri)
    except PlatformError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "TOKEN_EXCHANGE_FAILED", "message": f"WordPress.com token exchange failed — {e.message}", "detail": {}}},
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "TOKEN_EXCHANGE_FAILED", "message": f"WordPress.com token exchange failed — {str(e)[:200]}", "detail": {}}},
        )

    cred_json = json.dumps(tokens)
    encrypted = encrypt_credential(cred_json)
    await upsert_connection(db, client_id, "wordpress-com", encrypted)

    result: dict = {"platform": "wordpress-com", "connected": True}
    if tokens.get("blog_url"):
        result["account_identifier"] = tokens["blog_url"]
    return result


class GitHubConnectRequest(BaseModel):
    installation_id: str

    @field_validator("installation_id")
    @classmethod
    def validate_numeric(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("installation_id must be numeric")
        return v


class GitHubRepoPatchRequest(BaseModel):
    repo_full_name: str

    @field_validator("repo_full_name")
    @classmethod
    def validate_repo_format(cls, v: str) -> str:
        import re
        if not re.match(r"^[a-zA-Z0-9._-]+/[a-zA-Z0-9._\-]+$", v):
            raise ValueError("repo_full_name must be in 'owner/repo' format")
        return v


def _403_not_owner() -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={"error": {"code": "FORBIDDEN", "message": "You do not own this client.", "detail": {}}},
    )


def _check_github_ownership(client, user_id: uuid.UUID) -> None:
    if not client or client.user_id != user_id:
        raise _403_not_owner()


@router.post("/clients/{client_id}/connections/github", status_code=201)
async def connect_github(
    client_id: uuid.UUID,
    body: GitHubConnectRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    user_id = _parse_user_id(current_user)
    client = await get_client(db, client_id)
    _check_github_ownership(client, user_id)

    try:
        token_data = await github_integration.get_installation_token(body.installation_id)
    except PlatformError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "GITHUB_TOKEN_EXCHANGE_FAILED", "message": e.message, "detail": {}}},
        )

    cred_json = json.dumps({
        "installation_id": body.installation_id,
        "installation_token": token_data["token"],
        "expires_at": token_data["expires_at"],
        "repo_full_name": None,
    })
    encrypted = encrypt_credential(cred_json)
    await upsert_connection(db, client_id, "github_pages", encrypted)

    return {"platform": "github_pages", "connected": True, "account_identifier": None}


@router.patch("/clients/{client_id}/connections/github/repo", status_code=200)
async def select_github_repo(
    client_id: uuid.UUID,
    body: GitHubRepoPatchRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    user_id = _parse_user_id(current_user)
    client = await get_client(db, client_id)
    _check_github_ownership(client, user_id)

    connections = await get_connections_for_client(db, client_id)
    github_conn = next((c for c in connections if c.platform == "github_pages"), None)
    if not github_conn:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "GitHub connection not found.", "detail": {}}},
        )

    try:
        cred = json.loads(decrypt_credential(github_conn.encrypted_credentials))
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "CREDENTIAL_ERROR", "message": "Failed to read GitHub credentials.", "detail": {}}},
        )
    cred["repo_full_name"] = body.repo_full_name
    encrypted = encrypt_credential(json.dumps(cred))
    await upsert_connection(db, client_id, "github_pages", encrypted)

    return {"platform": "github_pages", "connected": True, "account_identifier": body.repo_full_name}


async def _refresh_github_token_if_needed(cred: dict, db: AsyncSession, client_id: uuid.UUID) -> dict:
    """Refresh the GitHub installation token if within 5 minutes of expiry. Returns updated cred."""
    from datetime import datetime, timedelta, timezone

    expires_at = cred.get("expires_at", "")
    needs_refresh = True
    if expires_at:
        try:
            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            needs_refresh = datetime.now(timezone.utc) >= expiry - timedelta(minutes=5)
        except ValueError:
            pass

    if needs_refresh:
        installation_id = cred.get("installation_id")
        if not installation_id:
            raise HTTPException(
                status_code=409,
                detail={"error": {"code": "INVALID_CREDENTIAL", "message": "GitHub connection is missing installation_id.", "detail": {}}},
            )
        try:
            token_data = await github_integration.get_installation_token(installation_id)
        except PlatformError as e:
            raise HTTPException(
                status_code=400,
                detail={"error": {"code": "GITHUB_TOKEN_REFRESH_FAILED", "message": e.message, "detail": {}}},
            )
        cred["installation_token"] = token_data["token"]
        cred["expires_at"] = token_data["expires_at"]
        encrypted = encrypt_credential(json.dumps(cred))
        await upsert_connection(db, client_id, "github_pages", encrypted)

    return cred


@router.get("/clients/{client_id}/connections/github/repos")
async def list_github_repos(
    client_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    user_id = _parse_user_id(current_user)
    client = await get_client(db, client_id)
    _check_github_ownership(client, user_id)

    connections = await get_connections_for_client(db, client_id)
    github_conn = next((c for c in connections if c.platform == "github_pages"), None)
    if not github_conn:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "GitHub connection not found.", "detail": {}}},
        )

    try:
        cred = json.loads(decrypt_credential(github_conn.encrypted_credentials))
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "CREDENTIAL_ERROR", "message": "Failed to read GitHub credentials.", "detail": {}}},
        )

    if not cred.get("installation_id"):
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "INVALID_CREDENTIAL", "message": "GitHub connection is missing installation_id.", "detail": {}}},
        )

    cred = await _refresh_github_token_if_needed(cred, db, client_id)

    try:
        repos = await github_integration.get_installation_repositories(cred["installation_token"])
    except PlatformError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "GITHUB_REPOS_FETCH_FAILED", "message": e.message, "detail": {}}},
        )

    return {"repos": repos}


@router.post("/clients/{client_id}/connections/github/detect", status_code=200)
async def detect_github_framework(
    client_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    user_id = _parse_user_id(current_user)
    client = await get_client(db, client_id)
    _check_github_ownership(client, user_id)

    connections = await get_connections_for_client(db, client_id)
    github_conn = next((c for c in connections if c.platform == "github_pages"), None)
    if not github_conn:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "GitHub connection not found.", "detail": {}}},
        )

    try:
        cred = json.loads(decrypt_credential(github_conn.encrypted_credentials))
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "CREDENTIAL_ERROR", "message": "Failed to read GitHub credentials.", "detail": {}}},
        )

    repo_full_name = cred.get("repo_full_name")
    if not repo_full_name:
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "NO_REPO_SELECTED", "message": "No repository selected. Select a repository first.", "detail": {}}},
        )

    cred = await _refresh_github_token_if_needed(cred, db, client_id)

    if not cred.get("installation_token"):
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "INVALID_CREDENTIAL", "message": "GitHub connection is missing installation_token.", "detail": {}}},
        )

    try:
        result = await repo_detection.detect_framework(cred["installation_token"], repo_full_name)
    except PlatformError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "GITHUB_DETECTION_FAILED", "message": e.message, "detail": {}}},
        )

    cred["detected_framework"] = result["detected_framework"]
    cred["publish_path"] = result["publish_path"]
    cred["confidence"] = result["confidence"]
    cred["signals"] = result["signals"]
    cred["candidates"] = result["candidates"]
    encrypted = encrypt_credential(json.dumps(cred))
    await upsert_connection(db, client_id, "github_pages", encrypted)

    return result


class FrameworkSelectRequest(BaseModel):
    detected_framework: str
    publish_path: str | None = None

    @field_validator("detected_framework")
    @classmethod
    def validate_framework(cls, v: str) -> str:
        from app.services.repo_detection import SELECTABLE_FRAMEWORKS
        if v not in SELECTABLE_FRAMEWORKS:
            raise ValueError(f"detected_framework must be one of {sorted(SELECTABLE_FRAMEWORKS)}")
        return v


@router.patch("/clients/{client_id}/connections/github/framework", status_code=200)
async def select_github_framework(
    client_id: uuid.UUID,
    body: FrameworkSelectRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    user_id = _parse_user_id(current_user)
    client = await get_client(db, client_id)
    _check_github_ownership(client, user_id)

    connections = await get_connections_for_client(db, client_id)
    github_conn = next((c for c in connections if c.platform == "github_pages"), None)
    if not github_conn:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "GitHub connection not found.", "detail": {}}},
        )

    try:
        cred = json.loads(decrypt_credential(github_conn.encrypted_credentials))
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "CREDENTIAL_ERROR", "message": "Failed to read GitHub credentials.", "detail": {}}},
        )

    if not cred.get("repo_full_name"):
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "NO_REPO_SELECTED", "message": "No repository selected. Select a repository first.", "detail": {}}},
        )

    from app.services.repo_detection import FRAMEWORK_PUBLISH_PATHS
    framework = body.detected_framework
    if body.publish_path is not None:
        if ".." in body.publish_path or body.publish_path.startswith("/"):
            raise HTTPException(
                status_code=400,
                detail={"error": {"code": "INVALID_PATH", "message": "publish_path must not contain '..' or a leading '/'.", "detail": {}}},
            )
    resolved_path = body.publish_path or FRAMEWORK_PUBLISH_PATHS[framework]
    cred["detected_framework"] = framework
    cred["publish_path"] = resolved_path
    cred["confidence"] = "high"
    cred["signals"] = []
    cred["candidates"] = []
    encrypted = encrypt_credential(json.dumps(cred))
    await upsert_connection(db, client_id, "github_pages", encrypted)

    return {
        "detected_framework": framework,
        "publish_path": resolved_path,
        "confidence": "high",
        "signals": [],
        "candidates": [],
    }


class GitHubPublishRequest(BaseModel):
    mode: str

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        if v not in ("pr", "commit"):
            raise ValueError("mode must be 'pr' or 'commit'")
        return v


@router.post("/campaigns/{campaign_id}/publish/github", status_code=202)
async def publish_campaign_github(
    campaign_id: uuid.UUID,
    body: GitHubPublishRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    user_id = _parse_user_id(current_user)

    campaign = await get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Campaign not found.", "detail": {}}},
        )

    client = await get_client(db, campaign.client_id)
    if not client or client.user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "FORBIDDEN", "message": "You do not own this campaign.", "detail": {}}},
        )

    if campaign.status != "approved":
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "INVALID_STATUS", "message": "Only approved campaigns can be published to GitHub.", "detail": {}}},
        )

    if body.mode == "pr" and campaign.github_pr_url:
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "PR_ALREADY_OPEN", "message": "A pull request is already open for this campaign.", "detail": {"pr_url": campaign.github_pr_url}}},
        )

    connections = await get_connections_for_client(db, campaign.client_id)
    github_conn = next((c for c in connections if c.platform == "github_pages"), None)
    if not github_conn:
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "NO_GITHUB_CONNECTION", "message": "No GitHub connection found for this client.", "detail": {}}},
        )

    try:
        cred = json.loads(decrypt_credential(github_conn.encrypted_credentials))
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "CREDENTIAL_ERROR", "message": "Failed to read GitHub credentials.", "detail": {}}},
        )

    if not cred.get("repo_full_name") or not cred.get("detected_framework"):
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "INCOMPLETE_GITHUB_SETUP", "message": "Repository and framework must be configured before publishing.", "detail": {}}},
        )

    job = await create_job(db, job_type="github_publish", status="pending", campaign_id=campaign_id)
    await db.commit()

    background_tasks.add_task(publish_github_job, job.id, campaign_id, body.mode)

    return {"job_id": str(job.id)}


class GitHubSettingsRequest(BaseModel):
    direct_commit_default: bool


@router.patch("/clients/{client_id}/connections/github/settings", status_code=200)
async def update_github_settings(
    client_id: uuid.UUID,
    body: GitHubSettingsRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    user_id = _parse_user_id(current_user)
    client = await get_client(db, client_id)
    _check_github_ownership(client, user_id)

    connections = await get_connections_for_client(db, client_id)
    github_conn = next((c for c in connections if c.platform == "github_pages"), None)
    if not github_conn:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "GitHub connection not found.", "detail": {}}},
        )

    try:
        cred = json.loads(decrypt_credential(github_conn.encrypted_credentials))
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "CREDENTIAL_ERROR", "message": "Failed to read GitHub credentials.", "detail": {}}},
        )

    cred["direct_commit_default"] = body.direct_commit_default
    encrypted = encrypt_credential(json.dumps(cred))
    await upsert_connection(db, client_id, "github_pages", encrypted)

    return {"direct_commit_default": body.direct_commit_default}


@router.post("/campaigns/{campaign_id}/publish", status_code=202)
async def publish_campaign_now(
    campaign_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    user_id = _parse_user_id(current_user)

    campaign = await get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Campaign not found.", "detail": {}}},
        )

    # Ownership check via client
    client = await get_client(db, campaign.client_id)
    if not client or client.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Campaign not found.", "detail": {}}},
        )

    await check_trial_not_expired(user_id, db, "publish")

    if campaign.status != "approved":
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_STATUS_TRANSITION",
                    "message": "Only approved campaigns can be published.",
                    "detail": {},
                }
            },
        )

    connections = await get_connections_for_client(db, campaign.client_id)
    if not connections:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "NO_PLATFORM_CONNECTIONS",
                    "message": "No platform connections found. Connect a platform first.",
                    "detail": {},
                }
            },
        )

    # Create job record FIRST, then commit, then dispatch — critical invariant
    job = await create_job(db, job_type="publish", status="pending", campaign_id=campaign_id)
    await db.commit()

    background_tasks.add_task(run_publish, job.id, campaign_id)

    return {"job_id": str(job.id)}


class ScheduleRequest(BaseModel):
    scheduled_at: datetime

    @field_validator("scheduled_at")
    @classmethod
    def must_be_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("scheduled_at must include timezone information")
        return v


@router.post("/campaigns/{campaign_id}/publish/schedule", status_code=200)
async def schedule_campaign_publish(
    campaign_id: uuid.UUID,
    body: ScheduleRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    user_id = _parse_user_id(current_user)

    campaign = await get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Campaign not found.", "detail": {}}},
        )

    client = await get_client(db, campaign.client_id)
    if not client or client.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Campaign not found.", "detail": {}}},
        )

    await check_trial_not_expired(user_id, db, "schedule publishing")

    if campaign.status != "approved":
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_STATUS_TRANSITION", "message": "Only approved campaigns can be scheduled.", "detail": {}}},
        )

    if campaign.scheduled_at is not None:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "ALREADY_SCHEDULED", "message": "Campaign is already scheduled.", "detail": {}}},
        )

    scheduled_at_utc = body.scheduled_at.astimezone(timezone.utc).replace(tzinfo=None)
    if scheduled_at_utc <= datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "SCHEDULED_TIME_IN_PAST", "message": "Scheduled time must be in the future.", "detail": {}}},
        )

    job = await create_job(
        db,
        job_type="scheduled_publish",
        status="scheduled",
        campaign_id=campaign_id,
    )
    job.scheduled_at = scheduled_at_utc
    await update_campaign_scheduled_at(db, campaign_id, scheduled_at_utc)

    # Register scheduler job before committing so DB rolls back if registration fails.
    try:
        scheduler.add_job(
            run_publish,
            trigger=DateTrigger(run_date=scheduled_at_utc),
            args=[str(job.id), str(campaign_id)],
            id=str(job.id),
            replace_existing=True,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "SCHEDULER_ERROR", "message": "Failed to register scheduled job.", "detail": {}}},
        ) from exc

    await db.commit()

    return {"job_id": str(job.id), "scheduled_at": scheduled_at_utc.isoformat() + "Z"}


@router.delete("/campaigns/{campaign_id}/publish/schedule", status_code=200)
async def cancel_scheduled_publish(
    campaign_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    user_id = _parse_user_id(current_user)

    campaign = await get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Campaign not found.", "detail": {}}},
        )

    client = await get_client(db, campaign.client_id)
    if not client or client.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Campaign not found.", "detail": {}}},
        )

    job = await get_scheduled_job(db, campaign_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "No scheduled publish job found.", "detail": {}}},
        )

    try:
        scheduler.remove_job(str(job.id))
    except JobLookupError:
        pass

    await db.delete(job)
    await update_campaign_scheduled_at(db, campaign_id, None)
    await db.commit()

    return {"campaign_id": str(campaign_id), "status": "approved"}


class RetryRequest(BaseModel):
    platform: str  # "wordpress" | "webflow" | "x" | "linkedin"


@router.post("/campaigns/{campaign_id}/publish/retry", status_code=202)
async def retry_platform_publish(
    campaign_id: uuid.UUID,
    body: RetryRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    user_id = _parse_user_id(current_user)

    campaign = await get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Campaign not found.", "detail": {}}},
        )

    client = await get_client(db, campaign.client_id)
    if not client or client.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Campaign not found.", "detail": {}}},
        )

    await check_trial_not_expired(user_id, db, "publish")

    if campaign.status != "failed":
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_STATUS_TRANSITION",
                    "message": "Only failed campaigns can be retried.",
                    "detail": {},
                }
            },
        )

    job = await get_publish_job_for_campaign(db, campaign_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "No publish job found for this campaign.", "detail": {}}},
        )

    # Verify the platform is actually failed (not already published)
    error_details = json.loads(job.error_details or "{}")
    platform_result = error_details.get(body.platform)
    if platform_result == "success":
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "PLATFORM_ALREADY_PUBLISHED",
                    "message": f"{body.platform.capitalize()} has already published successfully.",
                    "detail": {},
                }
            },
        )

    if job.attempt_count >= 3:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "MAX_RETRIES_REACHED",
                    "message": f"Maximum retries reached for {body.platform.capitalize()}. Reconnect the platform and try again.",
                    "detail": {},
                }
            },
        )

    # Increment attempt count and mark platform as retrying
    job.attempt_count = (job.attempt_count or 0) + 1
    error_details[body.platform] = "retrying"
    job.status = "pending"
    job.error_details = json.dumps(error_details)
    db.add(job)
    await db.commit()

    background_tasks.add_task(run_publish_retry, job.id, campaign_id, body.platform)

    return {"job_id": str(job.id)}


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
