import httpx

from app.core.config import settings
from app.core.exceptions import PlatformError


async def exchange_code_for_token(code: str, redirect_uri: str) -> dict:
    """Exchange OAuth code for access token. Returns {"access_token": str, "scope": str}."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": settings.LINKEDIN_CLIENT_ID,
                "client_secret": settings.LINKEDIN_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if resp.status_code != 200:
        body = resp.json() if resp.content else {}
        detail = body.get("error_description") or body.get("error") or "token exchange failed"
        raise PlatformError("LinkedIn", resp.status_code, detail)
    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise PlatformError("LinkedIn", 200, "token exchange returned no access_token")
    return {"access_token": token, "scope": data.get("scope") or ""}


async def _get_linkedin_author_urn(access_token: str, client: httpx.AsyncClient) -> str:
    """Fetch the authenticated user's sub (person URN) from LinkedIn userinfo."""
    resp = await client.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}", "LinkedIn-Version": "202602"},
    )
    if resp.status_code == 401:
        raise PlatformError("LinkedIn", 401, "LinkedIn connection expired - reconnect your LinkedIn account in Connections")
    if resp.status_code != 200:
        raise PlatformError("LinkedIn", resp.status_code, "failed to get user profile")
    sub = resp.json().get("sub", "")
    if not sub:
        raise PlatformError("LinkedIn", 422, "LinkedIn profile missing 'sub' field, cannot construct author URN")
    return sub


async def upload_image(access_token: str, author_urn: str, image_bytes: bytes, org_id: str | None = None) -> str:
    """Upload an image to LinkedIn via initializeUpload + PUT. Returns image URN."""
    owner = f"urn:li:organization:{org_id}" if org_id is not None else f"urn:li:person:{author_urn}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Initialize upload
        init_resp = await client.post(
            "https://api.linkedin.com/rest/images?action=initializeUpload",
            headers={
                "Authorization": f"Bearer {access_token}",
                "LinkedIn-Version": "202602",
                "X-Restli-Protocol-Version": "2.0.0",
                "Content-Type": "application/json",
            },
            json={"initializeUploadRequest": {"owner": owner}},
        )
        if init_resp.status_code == 401:
            raise PlatformError("LinkedIn", 401, "LinkedIn connection expired - reconnect your LinkedIn account in Connections")
        if init_resp.status_code not in (200, 201):
            raise PlatformError("LinkedIn", init_resp.status_code, f"image initializeUpload failed: {init_resp.text[:200]}")

        value = init_resp.json().get("value", {})
        upload_url: str = value.get("uploadUrl", "")
        image_urn: str = value.get("image", "")

        if not upload_url or not image_urn:
            raise PlatformError("LinkedIn", 200, "initializeUpload response missing uploadUrl or image URN")

        # Upload binary — pre-signed URL, no Authorization header
        put_resp = await client.put(
            upload_url,
            content=image_bytes,
            headers={"Content-Type": "image/png"},
        )
        if put_resp.status_code not in (200, 201):
            raise PlatformError("LinkedIn", put_resp.status_code, f"image binary PUT failed: {put_resp.text[:200]}")

    return image_urn


async def create_post_with_image(access_token: str, author_urn: str, text: str, image_urn: str, org_id: str | None = None) -> str:
    """Create a LinkedIn post with an attached image. Returns post URN."""
    author = f"urn:li:organization:{org_id}" if org_id is not None else f"urn:li:person:{author_urn}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://api.linkedin.com/rest/posts",
            headers={
                "Authorization": f"Bearer {access_token}",
                "LinkedIn-Version": "202602",
                "X-Restli-Protocol-Version": "2.0.0",
                "Content-Type": "application/json",
            },
            json={
                "author": author,
                "commentary": text or "",
                "visibility": "PUBLIC",
                "distribution": {
                    "feedDistribution": "MAIN_FEED",
                    "targetEntities": [],
                    "thirdPartyDistributionChannels": [],
                },
                "content": {"media": {"altText": "Featured image", "id": image_urn}},
                "lifecycleState": "PUBLISHED",
                "isReshareDisabledByAuthor": False,
            },
        )
        if resp.status_code == 401:
            raise PlatformError("LinkedIn", 401, "LinkedIn connection expired - reconnect your LinkedIn account in Connections")
        if resp.status_code != 201:
            raise PlatformError("LinkedIn", resp.status_code, resp.json().get("message", "image post creation failed"))
        return resp.headers.get("x-restli-id", "")


async def create_ugc_post(access_token: str, blog_html: str, linkedin_text: str, org_id: str | None = None) -> str:
    """Create a LinkedIn UGC post. Returns the post URN.

    When org_id is provided, posts as urn:li:organization:{org_id} and skips the /v2/userinfo call.
    When org_id is None, posts as the authenticated user's personal profile.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        if org_id is not None:
            author = f"urn:li:organization:{org_id}"
        else:
            sub = await _get_linkedin_author_urn(access_token, client)
            author = f"urn:li:person:{sub}"

        post_resp = await client.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers={
                "Authorization": f"Bearer {access_token}",
                "LinkedIn-Version": "202602",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            json={
                "author": author,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": linkedin_text or ""},
                        "shareMediaCategory": "NONE",
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
            },
        )
    if post_resp.status_code == 401:
        raise PlatformError("LinkedIn", 401, "LinkedIn connection expired - reconnect your LinkedIn account in Connections")
    if post_resp.status_code not in (200, 201):
        raise PlatformError(
            "LinkedIn", post_resp.status_code, post_resp.json().get("message", "UGC post failed")
        )
    return post_resp.headers.get("x-restli-id", "")


async def get_user_name(access_token: str) -> str:
    """Fetch the authenticated LinkedIn user's display name."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}", "LinkedIn-Version": "202602"},
        )
    if resp.status_code != 200:
        return "unknown"
    return resp.json().get("name", "unknown")
