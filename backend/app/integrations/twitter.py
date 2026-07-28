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


async def upload_media(access_token: str, image_bytes: bytes, mime_type: str = "image/png") -> str:
    """Upload image to X via INIT/APPEND/FINALIZE chunked upload. Returns media_id string."""
    chunk_size = 1_048_576  # 1 MB

    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"Authorization": f"Bearer {access_token}"}

        # INIT
        init_resp = await client.post(
            "https://api.x.com/2/media/upload",
            headers=headers,
            data={
                "command": "INIT",
                "media_type": mime_type,
                "total_bytes": str(len(image_bytes)),
                "media_category": "tweet_image",
            },
        )
        if init_resp.status_code not in (200, 201):
            raise PlatformError("X", init_resp.status_code, f"media upload INIT failed: {init_resp.text[:200]}")
        _init_data = init_resp.json().get("data", {})
        media_id = _init_data.get("id", "")
        if not media_id:
            raise PlatformError("X", init_resp.status_code, f"media upload INIT response missing data.id: {init_resp.text[:200]}")

        # APPEND
        for segment_index, offset in enumerate(range(0, len(image_bytes), chunk_size)):
            chunk = image_bytes[offset : offset + chunk_size]
            append_resp = await client.post(
                "https://api.x.com/2/media/upload",
                headers=headers,
                data={"command": "APPEND", "media_id": media_id, "segment_index": str(segment_index)},
                files={"media": chunk},
            )
            if append_resp.status_code not in (200, 204):
                raise PlatformError("X", append_resp.status_code, f"media upload APPEND segment {segment_index} failed")

        # FINALIZE
        finalize_resp = await client.post(
            "https://api.x.com/2/media/upload",
            headers=headers,
            data={"command": "FINALIZE", "media_id": media_id},
        )
        if finalize_resp.status_code not in (200, 201):
            raise PlatformError("X", finalize_resp.status_code, f"media upload FINALIZE failed: {finalize_resp.text[:200]}")

    return media_id


async def create_tweet_with_media(access_token: str, text: str, media_id: str) -> str:
    """Post a tweet with an attached image. Returns the tweet ID."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://api.twitter.com/2/tweets",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={
                "text": (text or "")[:280],
                "media": {"media_ids": [media_id]},
            },
            params={"tweet.fields": "id,text"},
        )
    if resp.status_code == 429:
        raise PlatformError("X", 429, "rate limit exceeded — retry later")
    if resp.status_code != 201:
        raise PlatformError("X", resp.status_code, resp.json().get("detail", "tweet with media creation failed"))
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
