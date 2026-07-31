"""Meta Graph API integration (Instagram, Facebook Page, Threads).

All endpoints use Graph API v25.0.
"""
import asyncio
import logging
from typing import Optional

import httpx

from app.core.config import settings
from app.core.exceptions import PlatformError

logger = logging.getLogger(__name__)

META_API_VERSION = "v25.0"
META_GRAPH_BASE = f"https://graph.facebook.com/{META_API_VERSION}"


def _extract_error(resp: httpx.Response) -> str:
    """Extract a human-readable error message from a Meta API error response."""
    try:
        body = resp.json()
        return body.get("error", {}).get("message", resp.text[:200])
    except Exception:
        return resp.text[:200]


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


async def publish_instagram_feed_post(
    instagram_user_id: str,
    page_access_token: str,
    image_url: str,
    caption: str,
) -> str:
    """Create and publish an Instagram feed image post. Returns the published media_id."""
    caption_truncated = (caption or "")[:2200]

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{META_GRAPH_BASE}/{instagram_user_id}/media",
            data={
                "image_url": image_url,
                "caption": caption_truncated,
                "access_token": page_access_token,
            },
        )
    if resp.status_code != 200:
        raise PlatformError("instagram", resp.status_code, _extract_error(resp))
    container_id = resp.json().get("id", "")
    if not container_id:
        raise PlatformError("instagram", 200, "media container creation returned no id")

    for attempt in range(6):
        if attempt > 0:
            await asyncio.sleep(10)
        async with httpx.AsyncClient(timeout=15.0) as client:
            status_resp = await client.get(
                f"{META_GRAPH_BASE}/{container_id}",
                params={"fields": "status_code", "access_token": page_access_token},
            )
        status_code = status_resp.json().get("status_code", "")
        if status_code == "FINISHED":
            break
        if status_code in ("ERROR", "EXPIRED"):
            raise PlatformError("instagram", 422, f"container processing failed: {status_code}")
    else:
        raise PlatformError("instagram", 408, "instagram container processing timed out after 60s")

    async with httpx.AsyncClient(timeout=15.0) as client:
        pub_resp = await client.post(
            f"{META_GRAPH_BASE}/{instagram_user_id}/media_publish",
            data={"creation_id": container_id, "access_token": page_access_token},
        )
    if pub_resp.status_code != 200:
        raise PlatformError("instagram", pub_resp.status_code, _extract_error(pub_resp))
    media_id = pub_resp.json().get("id", "")
    if not media_id:
        raise PlatformError("instagram", 200, "media_publish returned no id")
    return media_id


async def publish_facebook_page_post(
    page_id: str,
    page_access_token: str,
    message: str,
    image_url: Optional[str] = None,
) -> str:
    """Post to a Facebook Page feed. Returns post ID."""
    payload: dict = {
        "message": (message or ""),
        "access_token": page_access_token,
    }
    if image_url:
        payload["link"] = image_url

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{META_GRAPH_BASE}/{page_id}/feed",
            data=payload,
        )
    if resp.status_code == 429:
        raise PlatformError("facebook_page", 429, "Facebook Page rate limit reached")
    if resp.status_code == 401:
        raise PlatformError("facebook_page", 401, "Facebook Page connection expired - reconnect in Connections")
    if resp.status_code != 200:
        raise PlatformError("facebook_page", resp.status_code, _extract_error(resp))
    post_id = resp.json().get("id", "")
    if not post_id:
        raise PlatformError("facebook_page", 200, "feed post returned no id")
    return post_id


async def publish_threads_post(
    threads_user_id: str,
    user_access_token: str,
    text: str,
) -> str:
    """Create and publish a Threads text post. Returns Threads post ID."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{META_GRAPH_BASE}/{threads_user_id}/threads",
            data={
                "media_type": "TEXT",
                "text": (text or ""),
                "access_token": user_access_token,
            },
        )
    if resp.status_code != 200:
        raise PlatformError("threads", resp.status_code, _extract_error(resp))
    container_id = resp.json().get("id", "")
    if not container_id:
        raise PlatformError("threads", 200, "threads container creation returned no id")

    async with httpx.AsyncClient(timeout=15.0) as client:
        pub_resp = await client.post(
            f"{META_GRAPH_BASE}/{threads_user_id}/threads_publish",
            data={"creation_id": container_id, "access_token": user_access_token},
        )
    if pub_resp.status_code == 429:
        raise PlatformError("threads", 429, "Threads rate limit reached. Try again later.")
    if pub_resp.status_code == 401:
        raise PlatformError("threads", 401, "Threads connection expired - reconnect in Connections")
    if pub_resp.status_code != 200:
        raise PlatformError("threads", pub_resp.status_code, _extract_error(pub_resp))
    post_id = pub_resp.json().get("id", "")
    if not post_id:
        raise PlatformError("threads", 200, "threads_publish returned no id")
    return post_id


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
