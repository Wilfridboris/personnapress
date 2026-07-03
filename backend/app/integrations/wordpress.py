import base64
import logging

import httpx
from bs4 import BeautifulSoup

from app.core.exceptions import PlatformError

logger = logging.getLogger(__name__)


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


def _extract_title(html: str) -> str:
    """Extract the first <h1> text from blog HTML."""
    soup = BeautifulSoup(html or "", "html.parser")
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return "Untitled"


async def _upload_featured_image(
    client: httpx.AsyncClient,
    site_url: str,
    headers: dict,
    image_url: str,
) -> int | None:
    """Download image from URL and upload to WordPress media library."""
    try:
        img_resp = await client.get(image_url, timeout=20.0)
        img_resp.raise_for_status()
        content_type = img_resp.headers.get("content-type", "image/png")
        media_headers = {
            **headers,
            "Content-Disposition": 'attachment; filename="featured.png"',
            "Content-Type": content_type,
        }
        media_resp = await client.post(
            f"{site_url}/wp-json/wp/v2/media",
            headers=media_headers,
            content=img_resp.content,
        )
        if media_resp.status_code in (200, 201):
            return media_resp.json().get("id")
    except Exception as exc:
        logger.warning("Featured image upload failed: %s", exc)
    return None


async def publish_post(creds: dict, campaign) -> str:
    """Draft-first publish. Returns the live post URL."""
    site_url = creds["site_url"].rstrip("/")
    username = creds.get("username", "admin")
    app_password = creds.get("credential") or creds.get("application_password", "")
    auth = base64.b64encode(f"{username}:{app_password}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Create draft
        draft_resp = await client.post(
            f"{site_url}/wp-json/wp/v2/posts",
            headers=headers,
            json={
                "title": _extract_title(campaign.blog_html),
                "content": campaign.blog_html,
                "status": "draft",
            },
        )
        draft_resp.raise_for_status()
        post_id = draft_resp.json()["id"]

        # Step 2: Upload featured image (non-blocking)
        media_id = None
        if campaign.image_url:
            media_id = await _upload_featured_image(client, site_url, headers, campaign.image_url)

        # Step 3: Publish
        patch_body: dict = {"status": "publish"}
        if media_id:
            patch_body["featured_media"] = media_id
        pub_resp = await client.patch(
            f"{site_url}/wp-json/wp/v2/posts/{post_id}",
            headers=headers,
            json=patch_body,
        )
        if pub_resp.status_code != 200:
            # Clean up draft to avoid orphan
            try:
                await client.delete(
                    f"{site_url}/wp-json/wp/v2/posts/{post_id}",
                    headers=headers,
                    params={"force": "true"},
                )
            except Exception as cleanup_exc:
                logger.warning("WordPress draft cleanup failed for post %s: %s", post_id, cleanup_exc)
            raise PlatformError(
                "wordpress", pub_resp.status_code, "publish step failed — draft cleaned up"
            )

        return pub_resp.json().get("link", "")
