import time

import httpx
import jwt

from app.core.config import settings
from app.core.exceptions import PlatformError

_GITHUB_API_VERSION = "2026-03-10"

GITHUB_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": _GITHUB_API_VERSION,
}


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
            headers={**GITHUB_HEADERS, "Authorization": f"Bearer {app_jwt}"},
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
            headers={**GITHUB_HEADERS, "Authorization": f"Bearer {installation_token}"},
        )
    if resp.status_code != 200:
        raise PlatformError("github", resp.status_code, resp.text[:300])
    return [
        {"full_name": r["full_name"], "private": r["private"]}
        for r in resp.json().get("repositories", [])
    ]


async def get_repo_root_contents(installation_token: str, repo_full_name: str) -> list[dict]:
    """Fetch root-level file listing. Returns list of {name, type, path} dicts."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"https://api.github.com/repos/{repo_full_name}/contents/",
            headers={**GITHUB_HEADERS, "Authorization": f"Bearer {installation_token}"},
        )
    if resp.status_code != 200:
        raise PlatformError("github", resp.status_code, "contents API error")
    data = resp.json()
    if not isinstance(data, list):
        return []
    return [{"name": item.get("name", ""), "type": item.get("type", "file"), "path": item.get("path", "")} for item in data if item.get("name")]


async def get_directory_contents(installation_token: str, repo_full_name: str, path: str) -> list[dict]:
    """Fetch directory listing. Returns [] if path doesn't exist (404) or is not a directory."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"https://api.github.com/repos/{repo_full_name}/contents/{path}",
            headers={**GITHUB_HEADERS, "Authorization": f"Bearer {installation_token}"},
        )
    if resp.status_code == 404:
        return []
    if resp.status_code != 200:
        raise PlatformError("github", resp.status_code, "contents API error")
    data = resp.json()
    return data if isinstance(data, list) else []
