import httpx

from app.core.config import settings
from app.core.exceptions import PlatformError


async def exchange_code_for_token(code: str, redirect_uri: str) -> str:
    """Exchange OAuth code for access token."""
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
    token = resp.json().get("access_token")
    if not token:
        raise PlatformError("LinkedIn", 200, "token exchange returned no access_token")
    return token


async def create_ugc_post(access_token: str, blog_html: str, linkedin_text: str) -> str:
    """Create a LinkedIn UGC post. Returns the post URN."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        profile_resp = await client.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={
                "Authorization": f"Bearer {access_token}",
                "LinkedIn-Version": "202602",
            },
        )
        if profile_resp.status_code != 200:
            raise PlatformError("LinkedIn", profile_resp.status_code, "failed to get user profile")
        author_urn = profile_resp.json().get("sub", "")
        if not author_urn:
            raise PlatformError("LinkedIn", 422, "LinkedIn profile missing 'sub' field — cannot construct author URN")

        post_resp = await client.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers={
                "Authorization": f"Bearer {access_token}",
                "LinkedIn-Version": "202602",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            json={
                "author": f"urn:li:person:{author_urn}",
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
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if resp.status_code != 200:
        return "unknown"
    return resp.json().get("name", "unknown")
