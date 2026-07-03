import logging
import re
import unicodedata

import httpx
from bs4 import BeautifulSoup

from app.core.exceptions import PlatformError

logger = logging.getLogger(__name__)


def _extract_title(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    h1 = soup.find("h1")
    return h1.get_text(strip=True) if h1 else "Untitled"


def _slugify(title: str) -> str:
    # Normalize to ASCII only (removes accented chars, CJK, etc.)
    slug = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    slug = slug.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = slug.strip("-")
    return slug or "post"


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


async def publish_post(creds: dict, campaign) -> str:
    """Create and publish a Webflow CMS item. Returns the item ID."""
    token = creds["token"]
    collection_id = creds["collection_id"]
    headers = {
        "Authorization": f"Bearer {token}",
        "accept": "application/json",
        "Content-Type": "application/json",
    }
    title = _extract_title(campaign.blog_html)
    async with httpx.AsyncClient(timeout=30.0) as client:
        create_resp = await client.post(
            f"https://api.webflow.com/v2/collections/{collection_id}/items",
            headers=headers,
            json={
                "isArchived": False,
                "isDraft": False,
                "fieldData": {
                    "name": title,
                    "slug": _slugify(title),
                    "post-body": campaign.blog_html,
                },
            },
        )
        if create_resp.status_code not in (200, 201):
            raise PlatformError("webflow", create_resp.status_code, "CMS item creation failed")
        item_id = create_resp.json()["id"]

        pub_resp = await client.post(
            f"https://api.webflow.com/v2/collections/{collection_id}/items/publish",
            headers=headers,
            json={"itemIds": [item_id]},
        )
        if pub_resp.status_code not in (200, 202):
            # Best-effort cleanup — delete the orphaned draft item
            try:
                await client.delete(
                    f"https://api.webflow.com/v2/collections/{collection_id}/items/{item_id}",
                    headers=headers,
                )
            except Exception as cleanup_exc:
                logger.warning("Webflow orphan cleanup failed for item %s: %s", item_id, cleanup_exc)
            raise PlatformError("webflow", pub_resp.status_code, "publish step failed — item cleaned up")
        return item_id
