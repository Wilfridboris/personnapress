"""Meta Graph API integration (Instagram, Facebook Page, Threads).

All endpoints use Graph API v25.0.
"""
import logging
from typing import Optional

import httpx

from app.core.config import settings
from app.core.exceptions import PlatformError

logger = logging.getLogger(__name__)

META_API_VERSION = "v25.0"
META_GRAPH_BASE = f"https://graph.facebook.com/{META_API_VERSION}"


async def exchange_code_for_short_lived_token(code: str, redirect_uri: str) -> str:
    """Exchange an OAuth authorization code for a short-lived user access token."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{META_GRAPH_BASE}/oauth/access_token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.META_APP_ID,
                "client_secret": settings.META_APP_SECRET,
                "redirect_uri": redirect_uri,
            },
        )
    if resp.status_code != 200:
        body = resp.json() if resp.content else {}
        detail = body.get("error", {}).get("message") or "token exchange failed"
        raise PlatformError("Meta", resp.status_code, detail)
    token = resp.json().get("access_token")
    if not token:
        raise PlatformError("Meta", 200, "token exchange returned no access_token")
    return token


async def exchange_short_lived_for_long_lived_token(short_lived_token: str) -> str:
    """Exchange a short-lived user token for a 60-day long-lived token."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{META_GRAPH_BASE}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": settings.META_APP_ID,
                "client_secret": settings.META_APP_SECRET,
                "fb_exchange_token": short_lived_token,
            },
        )
    if resp.status_code != 200:
        body = resp.json() if resp.content else {}
        detail = body.get("error", {}).get("message") or "long-lived token exchange failed"
        raise PlatformError("Meta", resp.status_code, detail)
    token = resp.json().get("access_token")
    if not token:
        raise PlatformError("Meta", 200, "long-lived token exchange returned no access_token")
    return token


async def discover_accounts(long_lived_user_token: str) -> list[dict]:
    """Discover Facebook Pages and linked Instagram Business Accounts.

    Returns the raw list of pages from /me/accounts with nested instagram_business_account fields.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{META_GRAPH_BASE}/me/accounts",
            params={
                "fields": "instagram_business_account{id,username},name,id,access_token",
                "access_token": long_lived_user_token,
            },
        )
    if resp.status_code != 200:
        body = resp.json() if resp.content else {}
        detail = body.get("error", {}).get("message") or "account discovery failed"
        raise PlatformError("Meta", resp.status_code, detail)
    return resp.json().get("data", [])


async def discover_threads_user_id(
    instagram_user_id: str,
    long_lived_user_token: str,
) -> Optional[str]:
    """Attempt to fetch the Threads user ID linked to an Instagram user.

    Returns the threads_user_id string if present, or None if the user does not have
    Threads connected or the field is absent. Non-fatal errors are logged as warnings.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{META_GRAPH_BASE}/{instagram_user_id}",
                params={
                    "fields": "threads_user_id",
                    "access_token": long_lived_user_token,
                },
            )
        if resp.status_code != 200:
            logger.warning(
                "Threads user ID discovery returned %s for instagram_user_id=%s",
                resp.status_code,
                instagram_user_id,
            )
            return None
        return resp.json().get("threads_user_id") or None
    except Exception:
        logger.warning(
            "Threads user ID discovery failed for instagram_user_id=%s",
            instagram_user_id,
            exc_info=True,
        )
        return None
