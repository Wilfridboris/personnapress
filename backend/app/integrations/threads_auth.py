"""Threads OAuth integration (separate from Meta Business App).

Threads uses graph.threads.net for auth (not graph.facebook.com).
Publishing still uses graph.threads.com/v1.0 (see meta.py).
"""
import httpx

from app.core.config import settings
from app.core.exceptions import PlatformError

THREADS_AUTH_BASE = "https://graph.threads.net"


async def exchange_code_for_short_lived_token(code: str, redirect_uri: str) -> str:
    """Exchange Threads OAuth code for a short-lived token (valid ~1 hour)."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{THREADS_AUTH_BASE}/oauth/access_token",
            data={
                "client_id": settings.THREADS_APP_ID,
                "client_secret": settings.THREADS_APP_SECRET,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
                "code": code,
            },
        )
    if resp.status_code != 200:
        try:
            msg = resp.json().get("error_message", resp.text[:200])
        except Exception:
            msg = resp.text[:200]
        raise PlatformError("threads", resp.status_code, msg)
    token = resp.json().get("access_token")
    if not token:
        raise PlatformError("threads", 0, "Missing access_token in Threads response")
    return token


async def exchange_short_lived_for_long_lived_token(short_lived_token: str) -> str:
    """Exchange short-lived Threads token for a 60-day long-lived token."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{THREADS_AUTH_BASE}/access_token",
            params={
                "grant_type": "th_exchange_token",
                "client_id": settings.THREADS_APP_ID,
                "client_secret": settings.THREADS_APP_SECRET,
                "access_token": short_lived_token,
            },
        )
    if resp.status_code != 200:
        try:
            msg = resp.json().get("error_message", resp.text[:200])
        except Exception:
            msg = resp.text[:200]
        raise PlatformError("threads", resp.status_code, msg)
    token = resp.json().get("access_token")
    if not token:
        raise PlatformError("threads", 0, "Missing access_token in Threads response")
    return token


async def get_threads_user(long_lived_token: str) -> dict:
    """Fetch Threads user info. Returns dict with 'id' and 'username' keys."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{THREADS_AUTH_BASE}/v1.0/me",
            params={
                "fields": "id,username",
                "access_token": long_lived_token,
            },
        )
    if resp.status_code != 200:
        try:
            msg = resp.json().get("error", {}).get("message", resp.text[:200])
        except Exception:
            msg = resp.text[:200]
        raise PlatformError("threads", resp.status_code, msg)
    return resp.json()
