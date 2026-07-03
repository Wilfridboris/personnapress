import base64

import httpx

from app.core.exceptions import PlatformError


async def validate_credentials(site_url: str, username: str, application_password: str) -> str:
    """Validate WordPress credentials. Returns the site URL on success."""
    token = base64.b64encode(f"{username}:{application_password}".encode()).decode()
    url = f"{site_url.rstrip('/')}/wp-json/wp/v2/users/me"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers={"Authorization": f"Basic {token}"})
    if resp.status_code == 401:
        raise PlatformError("wordpress", 401, "check your Application Password")
    if resp.status_code != 200:
        raise PlatformError("wordpress", resp.status_code, "connection test failed")
    return site_url
