import logging

import httpx

from app.core.config import settings
from app.core.exceptions import PlatformError
from app.integrations.wordpress import _extract_title

logger = logging.getLogger(__name__)


async def _fetch_primary_blog(access_token: str) -> tuple[str, str]:
    """Fetch the user's primary WordPress.com site.

    When scope=global is used without a specific blog parameter, WordPress.com
    returns blog_id=0 in the token response. We call /me/sites to resolve the
    actual blog ID from the user's account.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            "https://public-api.wordpress.com/rest/v1.1/me/sites",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if resp.status_code != 200:
        raise PlatformError(
            "wordpress-com", resp.status_code,
            "could not fetch your WordPress.com sites — please try reconnecting"
        )
    sites = resp.json().get("sites", [])
    if not sites:
        raise PlatformError(
            "wordpress-com", 200,
            "no WordPress.com site found on your account — create a site at wordpress.com first, then reconnect"
        )
    primary = next((s for s in sites if s.get("is_primary")), sites[0])
    blog_id = str(primary.get("ID") or "")
    if not blog_id or blog_id == "0":
        raise PlatformError("wordpress-com", 200, "could not determine your WordPress.com site ID")
    return blog_id, primary.get("URL", "")


async def exchange_code_for_tokens(code: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://public-api.wordpress.com/oauth2/token",
            data={
                "client_id": settings.WP_COM_CLIENT_ID,
                "client_secret": settings.WP_COM_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "code": code,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
        )
    if resp.status_code != 200:
        raise PlatformError("wordpress-com", resp.status_code, f"token exchange failed — {resp.text[:200]}")
    data = resp.json()
    if "access_token" not in data:
        raise PlatformError("wordpress-com", 200, "no access_token in response")

    access_token = data["access_token"]
    blog_id = str(data.get("blog_id") or "")
    blog_url = data.get("blog_url", "")

    # scope=global without a specific blog returns blog_id=0.
    # Resolve the user's primary site via /me/sites.
    if not blog_id or blog_id == "0":
        blog_id, blog_url = await _fetch_primary_blog(access_token)

    return {"access_token": access_token, "blog_id": blog_id, "blog_url": blog_url}


async def publish_post(creds: dict, campaign) -> str:
    """Publish to WordPress.com. Returns the live post URL."""
    access_token = creds["access_token"]
    blog_id = str(creds.get("blog_id") or "")
    if not blog_id or blog_id == "0":
        raise PlatformError("wordpress-com", 400, "invalid blog_id in stored credentials — disconnect and reconnect your WordPress.com account")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Upload featured image if present
        # WP.com media/new requires multipart/form-data (files= in httpx), not form-encoded (data=)
        # Response shape: {"media": [{"ID": 123, "URL": "..."}, ...], "errors": [...]}
        featured_media_id = None
        if campaign.image_url:
            try:
                media_resp = await client.post(
                    f"https://public-api.wordpress.com/rest/v1.1/sites/{blog_id}/media/new",
                    headers={"Authorization": f"Bearer {access_token}"},
                    files={"media_urls[0]": (None, campaign.image_url)},
                )
                if media_resp.status_code in (200, 201):
                    media_objects = media_resp.json().get("media", [])
                    if media_objects:
                        featured_media_id = media_objects[0].get("ID")
            except Exception as exc:
                logger.warning("WP.com featured image upload failed: %s", exc)

        # Step 2: Create post
        post_body: dict = {
            "title": _extract_title(campaign.blog_html),
            "content": campaign.blog_html,
            "status": "publish",
        }
        if featured_media_id:
            post_body["featured_image"] = str(featured_media_id)

        pub_resp = await client.post(
            f"https://public-api.wordpress.com/rest/v1.1/sites/{blog_id}/posts/new",
            headers=headers,
            json=post_body,
        )
        if pub_resp.status_code not in (200, 201):
            raise PlatformError("wordpress-com", pub_resp.status_code, f"publish failed — {pub_resp.text[:200]}")
        return pub_resp.json().get("URL", "")
