import httpx

from app.core.exceptions import PlatformError


async def validate_token(token: str) -> None:
    """Raise PlatformError if the token cannot authenticate against Webflow."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://api.webflow.com/v2/sites",
            headers={"Authorization": f"Bearer {token}", "accept": "application/json"},
        )
        if resp.status_code != 200:
            raise PlatformError("webflow", resp.status_code, "token validation failed")


async def fetch_collections(token: str) -> list[dict]:
    """Fetch Webflow CMS collections for the authenticated user's sites."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        sites_resp = await client.get(
            "https://api.webflow.com/v2/sites",
            headers={"Authorization": f"Bearer {token}", "accept": "application/json"},
        )
        if sites_resp.status_code != 200:
            raise PlatformError("webflow", sites_resp.status_code, "token validation failed")
        sites = sites_resp.json().get("sites", [])
        if not sites:
            raise PlatformError("webflow", 200, "no Webflow sites found for this token")
        site_id = sites[0]["id"]
        cols_resp = await client.get(
            f"https://api.webflow.com/v2/sites/{site_id}/collections",
            headers={"Authorization": f"Bearer {token}", "accept": "application/json"},
        )
        if cols_resp.status_code != 200:
            raise PlatformError("webflow", cols_resp.status_code, "collections fetch failed")
        return [
            {"id": c["id"], "name": c["displayName"]}
            for c in cols_resp.json().get("collections", [])
        ]
