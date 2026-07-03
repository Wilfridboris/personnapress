import httpx

from app.core.config import settings
from app.core.exceptions import PlatformError


async def exchange_code_for_tokens(
    code: str,
    code_verifier: str,
    redirect_uri: str,
) -> dict:
    """Exchange PKCE code for access + refresh tokens."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            "https://api.twitter.com/2/oauth2/token",
            data={
                "code": code,
                "grant_type": "authorization_code",
                "client_id": settings.X_CLIENT_ID,
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
            },
            auth=(settings.X_CLIENT_ID, settings.X_CLIENT_SECRET),
        )
    if resp.status_code != 200:
        raise PlatformError("X", resp.status_code, resp.json().get("error_description", "token exchange failed"))
    return resp.json()


async def create_tweet(access_token: str, text: str) -> str:
    """Post a tweet. Returns the tweet ID."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://api.twitter.com/2/tweets",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={"text": (text or "")[:280]},
            params={"tweet.fields": "id,text"},
        )
    if resp.status_code == 429:
        raise PlatformError("X", 429, "rate limit exceeded — retry later")
    if resp.status_code != 201:
        raise PlatformError("X", resp.status_code, resp.json().get("detail", "tweet creation failed"))
    tweet_id = resp.json().get("data", {}).get("id", "")
    if not tweet_id:
        raise PlatformError("X", 201, "tweet created but response missing data.id")
    return tweet_id


async def get_user_handle(access_token: str) -> str:
    """Fetch the authenticated user's Twitter handle."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://api.twitter.com/2/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if resp.status_code != 200:
        return "unknown"
    return resp.json().get("data", {}).get("username", "unknown")
