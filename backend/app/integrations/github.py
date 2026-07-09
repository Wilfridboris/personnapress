import time

import httpx
import jwt

from app.core.config import settings
from app.core.exceptions import PlatformError

_GITHUB_API_VERSION = "2026-03-10"


def generate_app_jwt() -> str:
    """Sign a short-lived JWT for GitHub App authentication (RS256, 9-minute validity)."""
    if not settings.GITHUB_APP_PRIVATE_KEY:
        raise PlatformError("github", 0, "GITHUB_APP_PRIVATE_KEY is not configured")
    now = int(time.time())
    payload = {
        "iss": settings.GITHUB_APP_CLIENT_ID,
        "iat": now - 60,   # 60 s in past to tolerate clock skew (GitHub requirement)
        "exp": now + 540,  # 9 minutes (max is 10)
    }
    private_key = settings.GITHUB_APP_PRIVATE_KEY.replace("\\n", "\n")
    return jwt.encode(payload, private_key, algorithm="RS256")


async def get_installation_token(installation_id: str) -> dict:
    """Exchange installation ID for a short-lived token. Returns {"token": ..., "expires_at": ...}."""
    app_jwt = generate_app_jwt()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": _GITHUB_API_VERSION,
            },
        )
    if resp.status_code != 201:
        raise PlatformError("github", resp.status_code, resp.text[:300])
    data = resp.json()
    token = data.get("token")
    expires_at = data.get("expires_at")
    if not token or not expires_at:
        raise PlatformError("github", 201, "Missing token or expires_at in GitHub response")
    return {"token": token, "expires_at": expires_at}


async def get_installation_repositories(installation_token: str) -> list[dict]:
    """List repositories accessible to the installation. Returns list of {full_name, private}."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            "https://api.github.com/installation/repositories",
            params={"per_page": 100},
            headers={
                "Authorization": f"Bearer {installation_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": _GITHUB_API_VERSION,
            },
        )
    if resp.status_code != 200:
        raise PlatformError("github", resp.status_code, resp.text[:300])
    return [
        {"full_name": r["full_name"], "private": r["private"]}
        for r in resp.json().get("repositories", [])
    ]
